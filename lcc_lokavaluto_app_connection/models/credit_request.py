import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools import after_commit

_logger = logging.getLogger(__name__)


class CreditRequest(models.Model):
    """Credit request to follow the top up process for user wallets."""

    _name = "credit.request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Represents the request of a user to transform state currency in alternative currency."

    amount = fields.Float("Amount", required=True, tracking=True)
    wallet_id = fields.Many2one(
        "res.partner.backend",
        string="Wallet",
        required=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        related="wallet_id.partner_id",
        readonly=True,
    )
    alt_currency_id = fields.Many2one(
        "res.alt.currency",
        related="wallet_id.alt_currency_id",
        string="Currency",
    )
    state = fields.Selection(
        [
            ("open", "Open"),
            ("pending", "Pending"),
            ("error", "Error"),
            ("done", "Done"),
        ],
        string="State",
        required=True,
        default="open",
        tracking=True,
    )

    invoice_id = fields.Many2one("account.move", string="Linked Invoice", tracking=True)
    order_id = fields.Many2one("sale.order", string="Linked Sale Order", tracking=True)

    transaction_data = fields.Char("Transaction Message", tracking=True)
    error_message = fields.Char("Error Message", tracking=True)

    limit_credit_aggregation = fields.Boolean("Limit credit aggregation", tracking=True)
    max_credit_amount = fields.Float("Maximum amount of credit allowed", tracking=True)

    requester_id = fields.Many2one("res.partner", string="Requester", tracking=True)

    @api.model
    def create(self, vals):
        if vals.get("amount", 0) == 0.0:
            msg = "Credit request can't be created with a null amount."
            raise UserError(msg)
        if vals.get("amount", 0) > 2**46 - 1:
            ## amount field is declared as a float in postgresql it is a double precision
            ## which can store values up to 2**53 - 1, but we need precision on the decimal part
            ## up to 2 digits, so we limit the amount to 2**46 - 1
            msg = "Credit request can't be created with an amount > 2**46 - 1."
            raise UserError(
                msg,
            )

        no_order = vals.pop("no_order", False)

        vals["requester_id"] = vals.get("requester_id", self.env.user.partner_id.id)

        res = super().create(vals)

        if no_order:
            return res

        # Create Sale Order to get credit request payment
        res.create_credit_sale_order()
        return res

    def write(self, vals):
        if any(request.state == "done" for request in self):
            msg = "You can't modify a done credit request."
            raise UserError(msg)
        if "amount" in vals and vals["amount"] > 2**46 - 1:
            ## amount field is declared as a float in postgresql it is a double precision
            ## which can store values up to 2**53 - 1, but we need precision on the decimal part
            ## up to 2 digits, so we limit the amount to 2**46 - 1
            msg = "Credit request can't be created with an amount > 2**46 - 1."
            raise UserError(
                msg,
            )

        if vals.get("state") == "pending":
            # Launch after_commit function to launch the credit request once the request state is commited
            self._check_pending_requests_to_credit()

        return super().write(vals)

    @after_commit
    def _check_pending_requests_to_credit(self) -> None:
        for request in self:
            if (
                request.alt_currency_id.activate_automatic_topup
                and request.state == "pending"
            ):
                # The top up has been paid, the credit process can start
                request.sudo().credit_wallet()

    def unlink(self):
        for request in self:
            if request.state == "pending" or (
                request.invoice_id and request.invoice_id.state != "draft"
            ):
                msg = "You can't delete a credit request linked with a confirmed or paid invoice."
                raise UserError(
                    msg,
                )
            if request.state == "error":
                msg = "You can't delete a credit request in Error. Please solve the issue."
                raise UserError(
                    msg,
                )
            if request.state == "done":
                msg = (
                    "You can't delete a done credit request. Please archive it instead."
                )
                raise UserError(
                    msg,
                )

            if request.order_id:
                if request.order_id and request.order_id.state not in {
                    "draft",
                    "cancel",
                }:
                    request.order_id._action_cancel()
                request.order_id.unlink()
            if request.invoice_id and request.invoice_id.state == "draft":
                request.invoice_id.unlink()
        return super().unlink()

    def compute_amount_to_credit(self):
        """Compute correct amount function of wallet balance
        if limited credit aggregation.
        """
        self.ensure_one()
        amount = self.amount
        if amount == 0 or not self.wallet_id:
            return {
                "error": True,
                "error_message": "Missing information in the credit request (amount or Wallet)",
            }
        if self.limit_credit_aggregation:
            wallet_balance_data = self.wallet_id.get_wallet_balance()
            if not wallet_balance_data.get("success", False):
                return {
                    "error": True,
                    "error_message": wallet_balance_data.get(
                        "error_message",
                        "Error when trying to get wallet balance",
                    ),
                }
            amount = min(
                self.max_credit_amount - wallet_balance_data.get("response"),
                self.amount,
            )
            if amount <= 0:
                return {
                    "error": True,
                    "error_message": "Wallet balance above the Max credit amount allowed",
                }
        return {"amount": amount, "error": False}

    def create_credit_sale_order(self) -> None:
        Order = self.env["sale.order"]
        Line = self.env["sale.order.line"]

        for request in self:
            order_vals = {
                "partner_id": request.partner_id.id,
                "user_id": 1,  # __system__ user ID
            }
            order_vals = Order.play_onchanges(order_vals, ["partner_id"])
            order_id = Order.create(order_vals)
            line_vals = {
                "order_id": order_id.id,
                "product_id": self.alt_currency_id.currency_unit_product_id.id,
            }
            line_vals = Line.play_onchanges(line_vals, ["product_id"])
            line_vals.update(
                {
                    "product_uom_qty": request.amount,
                    "price_unit": 1,
                },
            )
            _logger.debug(f"NUMERIC LCC ORDER LINE: {line_vals}")
            Line.create(line_vals)
            order_id.write(
                {"state": "sent", "require_signature": False, "require_payment": True},
            )
            _logger.debug(f"Credit request sale order created: {order_id.name}")
            request.order_id = order_id.id

    def credit_wallet(self) -> None:
        """Send credit order to the wallet."""
        for record in self:
            if record.state not in {"pending", "error"}:
                continue

            # Check if we have the needed data to perform the top up process
            amount_data = record.compute_amount_to_credit()

            if not amount_data.get("error", False):
                # Ask wallet to perform top up process
                res = record.wallet_id.credit_wallet(amount_data.get("amount"))

                # Update request status
                if res.get("success", False):
                    vals = {
                        "state": "done",
                        "transaction_data": res.get("response", ""),
                        "amount": amount_data.get("amount"),
                    }
                else:
                    vals = {
                        "state": "error",
                        "transaction_data": res.get("response", ""),
                        "error_message": res.get("error", "No error message received."),
                    }
            else:
                vals = {
                    "state": "error",
                    "error_message": amount_data.get(
                        "error_message",
                        "Error defining amount to credit",
                    ),
                }
            record.write(vals)

    def validate(self) -> None:
        """Function to use when another software is in charge of the top up process,
        and needs to inform Odoo that the process has been performed with success.
        """
        for request in self:
            request.write({"state": "done"})

    def try_again(self) -> None:
        """Function available when the request is in error state, to send a new credit request."""
        for request in self:
            if request.state == "error":
                request.write({"state": "pending"})
