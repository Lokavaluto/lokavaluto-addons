from odoo import models, fields, api
from odoo.exceptions import UserError


class DebitRequest(models.Model):
    """Debit request to follow the reconversion process for wallet users"""

    _sql_constraints = [
        (
            "transaction_id_uniq",
            "unique(transaction_id)",
            "Transaction ID must be unique, a request already exists with this transaction ID!",
        ),
    ]

    _name = "debit.request"

    active = fields.Boolean(default=True, tracking=True)
    amount = fields.Float("Amount", required=True)
    wallet_id = fields.Many2one("res.partner.backend", string="Wallet", required=True)
    partner_id = fields.Many2one(
        "res.partner", related="wallet_id.partner_id", readonly=True
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),  # request created, some fields values still missing
            (
                "received",
                "Received",
            ),  # all transaction data received, draft invoiced created
            ("invoiced", "Invoiced"),  # invoiced validated/sent
            ("paid", "Paid"),  # all invoices have been paid
            ("cancelled", "Cancelled"),  # debit request cancelled
        ],
        required=True,
        string="State",
        default="draft",
    )
    transaction_id = fields.Char("Transaction ID")
    transaction_timestamp = fields.Datetime("Transaction Timestamp")
    debit_move_id = fields.Many2one("account.move", string="Debit Invoice")
    debit_move_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
        ],
        string="Debit Invoice State",
        default="draft",
    )
    commission_rule_id = fields.Many2one(
        "commission.rule",
        string="Commission Rule",
    )
    commission_move_id = fields.Many2one("account.move", string="Commission Invoice")
    commission_move_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
        ],
        string="Commission Invoice State",
        default="draft",
    )

    @api.model
    def create(self, vals):
        res = super(DebitRequest, self).create(vals)
        for request in res:
            if request.wallet_id:
                request.commission_rule_id = (
                    request.wallet_id.get_wallet_commission_rule()
                )
            try:
                if request.is_ready_to_invoice():
                    request.create_invoices()
            except UserError:
                # Missing data in not critical at creation step.
                pass
        return res

    def write(self, vals):
        if vals.get("wallet_id") and not vals.get("commission_rule_id"):
            vals["commission_rule_id"] = (
                self.env["res.partner.backend"]
                .browse(vals["wallet_id"])
                .get_wallet_commission_rule()
                .id
            )
        return super(DebitRequest, self).write(vals)

    def unlink(self):
        for request in self:
            if request.state == "cancelled":
                raise UserError(
                    "You can't delete a cancelled debit request. Please archive it instead."
                )
            elif request.state == "paid":
                raise UserError(
                    "You can't delete a paid debit request. Please archive it instead."
                )
            if request.debit_move_id:
                if request.debit_move_id.state != "draft":
                    raise UserError(
                        "You can't delete a debit request linked with a posted or paid invoice."
                    )
                request.debit_move_id.unlink()
            if request.commission_move_id:
                if request.commission_move_id.state != "draft":
                    raise UserError(
                        "You can't delete a debit request linked with a posted or paid invoice."
                    )
                request.commission_move_id.unlink()
        return super(DebitRequest, self).unlink()

    def compute_state(self):
        for request in self:
            if not request.debit_move_id:
                request.state = "draft"
                continue

            if not request.commission_move_id:
                # If there is no commission invoice, the debit invoice status defines the request status.
                request.state = self._convert_status(request.debit_move_state)
                continue

            if request.debit_move_state == "cancelled":
                # Debit move cancellation means there is no debit to perform, then all the process is cancelled.
                request.state = "cancelled"
                continue

            if request.commission_move_state == "cancelled":
                # If the commission invoice is cancelled, we do not consider it anymore for the request status.
                request.state = self._convert_status(request.debit_move_state)
                continue

            if (
                request.debit_move_state == "draft"
                or request.commission_move_state == "draft"
            ):
                # If any of the invoices is in Draft, the request is still considered as "received"
                request.state = self._convert_status("draft")
                continue

            if (
                request.debit_move_state == "posted"
                or request.commission_move_state == "posted"
            ):
                request.state = self._convert_status("posted")
                continue

            if (
                request.debit_move_state == "paid"
                or request.commission_move_state == "paid"
            ):
                request.state = self._convert_status("paid")

    def _convert_status(self, status):
        if status == "draft":
            return "received"
        if status == "posted":
            return "invoiced"
        if status == "paid":
            return "paid"

    def is_ready_to_invoice(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError("Amount must be superior to zero.")
        if not self.wallet_id:
            raise UserError("The wallet is missing.")
        if not self.transaction_id:
            raise UserError("The transaction ID is missing.")
        return True

    #############################
    ## INVOICE CREATION PROCESSES
    #############################

    def create_invoices(self):
        self.create_debit_invoices()
        self.create_commission_invoices()
        self.compute_state()

    def create_debit_invoices(self):
        for request in self:
            self.is_ready_to_invoice()
            # get invoices data
            debit_invoice_data = request._get_debit_invoice_data()
            # create invoices
            invoice = self.env["account.move"].create(debit_invoice_data)
            request.debit_move_id = invoice.id

    def _get_debit_invoice_data(self):
        self.ensure_one()
        return {
            "move_type": "in_invoice",
            "partner_id": self.partner_id.id,
            "invoice_line_ids": [(0, 0, self._get_debit_invoice_line_values())],
        }

    def _get_debit_invoice_line_values(self):
        self.ensure_one()
        product_id = self.wallet_id.get_lcc_product()
        invoice_line_values = {
            "product_id": product_id.id,
            "quantity": self.amount,
            "price_unit": product_id.standard_price,
        }
        return invoice_line_values

    def create_commission_invoices(self):
        for request in self:
            if not self.commission_rule_id:
                continue
            self.is_ready_to_invoice()
            # get invoices data
            commission_invoice_data = request._get_commission_invoice_data()
            # create invoices
            invoice = self.env["account.move"].create(commission_invoice_data)
            request.commission_move_id = invoice.id

    def _get_commission_invoice_data(self):
        self.ensure_one()
        return {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_line_ids": [(0, 0, self._get_commission_invoice_line_values())],
        }

    def _get_commission_invoice_line_values(self):
        self.ensure_one()
        product_id = self.env.user.company_id.commission_product_id
        commission_amount = self.commission_rule_id.calculate_commission_amount(
            self.amount
        )
        invoice_line_values = {
            "product_id": product_id.id,
            "quantity": 1,
            "price_unit": commission_amount,
        }
        return invoice_line_values
