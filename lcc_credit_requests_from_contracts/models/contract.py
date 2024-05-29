from odoo import fields, models, api


class ContractContract(models.Model):
    _inherit = "contract.contract"

    create_credit_requests = fields.Boolean("Create Credit Requests")
    wallet_id = fields.Many2one("res.partner.backend", string="Wallet to credit")

    def _prepare_credit_request_values(self, invoice):
        values = {
            "amount": invoice.amount_total,
            "partner_id": invoice.partner_id.id,
            "wallet_id": invoice.contract_id.wallet_id.id,
            "invoice_id": invoice.id,
            "no_order": True,
        }
        return values

    def _prepare_invoice(self, date_invoice, journal=None):
        invoice_vals = super()._prepare_invoice(date_invoice, journal)
        invoice_vals['contract_id'] = self.id
        return invoice_vals

    def _recurring_create_invoice(self, date_ref=False):
        invoices = super()._recurring_create_invoice(date_ref)
        for invoice in invoices:
            if invoice.has_numeric_lcc_products and invoice.contract_id.create_credit_requests:
                values = self._prepare_credit_request_values(invoice)
                self.env["credit.request"].create(values)
        return invoices
