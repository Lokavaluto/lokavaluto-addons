from odoo import models, fields, api
from odoo.exceptions import UserError


class CreditRequest(models.Model):
    """Credit request to follow the top up process for user wallets"""

    _name = "credit.request"

    amount = fields.Float("Amount", required=True)
    wallet_id = fields.Many2one("res.partner.backend", string="Wallet", required=True)
    partner_id = fields.Many2one(
        "res.partner", related="wallet_id.partner_id", readonly=True
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
    )

    invoice_id = fields.Many2one("account.move", string="Linked Invoice")
    order_id = fields.Many2one("sale.order", string="Linked Sale Order")

    transaction_data = fields.Char("Transaction Message")
    error_message = fields.Char("Error Message")

    @api.model
    def create(self, vals):
        if vals.get("amount", False) == 0.0:
            raise UserError("Credit resquest can't be created with a null amount.")
        create_order = vals.pop("create_order", False)
        res = super(CreditRequest, self).create(vals)

        if vals.get("no_order", False):
            return res

        # Create Sale Order to get credit request payment
        new_order = res.partner_id.create_numeric_lcc_order(
            res.wallet_id, res.amount
        )
        res.order_id = new_order.id
        return res

    def write(self, vals):
        if any(request.state == "done" for request in self):
            raise UserError("You can't modify a done credit request.")
        res = super(CreditRequest, self).write(vals)
        for request in self:
            if request.state == "pending":
                # The top up has been paid, the credit process can start
                if request.partner_id.company_id.activate_automatic_topup:
                    request.credit_wallet()
        return res

    def unlink(self):
        for request in self:
            if request.state == "pending" or (
                request.invoice_id and request.invoice_id.state != "draft"
            ):
                raise UserError(
                    "You can't delete a credit request linked with a confirmed or paid invoice."
                )
            elif request.state == "error":
                raise UserError(
                    "You can't delete a credit request in Error. Please solve the issue."
                )
            elif request.state == "done":
                raise UserError(
                    "You can't delete a done credit request. Please archive it instead."
                )

            if request.order_id:
                if request.order_id and request.order_id.state not in (
                    "draft",
                    "cancel",
                ):
                    request.order_id.action_cancel()
                request.order_id.unlink()
            if request.invoice_id and request.invoice_id.state == "draft":
                request.invoice_id.unlink()
        return super(CreditRequest, self).unlink()

    def credit_wallet(self):
        """Send credit order to the wallet."""
        for record in self:
            # Check if we have the needed data to perform the top up process
            if record.amount == 0 or not record.wallet_id:
                raise Exception(
                    "Missing information in the credit request - Top up cancelled."
                )

            # Ask wallet to perform top up process
            res = record.wallet_id.credit_wallet(record.amount)

            # Update request status
            if res.get("success", False):
                vals = {
                    "state": "done",
                    "transaction_data": res.get("response", ""),
                }
            else:
                vals = {
                    "state": "error",
                    "transaction_data": res.get("response", ""),
                    "error_message": res.get("error", "No error message received."),
                }
            record.write(vals)

    def validate(self):
        """Function to use when another software is in charge of the top up process,
        and needs to inform Odoo that the process has been performed with success."""
        for request in self:
            request.write({"state": "done"})

    def try_again(self):
        """Function available when the request is in error state, to send a new credit request."""
        for request in self:
            if request.state == "error":
                request.write({"state": "pending"})
