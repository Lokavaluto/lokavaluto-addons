from odoo import fields, models


class ContractContract(models.Model):
    _inherit = "contract.contract"

    create_credit_requests = fields.Boolean("Create Credit Requests")
    wallet_id = fields.Many2one("res.partner.backend", string="Wallet to credit")

    def _prepare_credit_request_values(self, invoice):
        values = {
            "amount": invoice.amount_total,
            "partner_id": invoice.partner_id.id,
            "wallet_id": self.wallet_id.id,
            "invoice_id": invoice.id,
            "create_order": False,
        }
        return values

    def _recurring_create_invoice(self, date_ref=False):
        invoices = super()._recurring_create_invoice(date_ref)
        if not (self.create_credit_requests and self.wallet_id):
            return invoices
        for invoice in invoices:
            if invoice.has_numeric_lcc_products:
                values = self._prepare_credit_request_values(invoice)
                self.env["credit.request"].create(values)
        return invoices
