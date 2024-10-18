from odoo import fields, models, api


class ContractContract(models.Model):
    _inherit = "contract.contract"

    create_credit_requests = fields.Boolean("Create Credit Requests")
    wallet_id = fields.Many2one("res.partner.backend", string="Wallet to credit")
    different_credit_request_amount = fields.Boolean("Different credit request amount")
    credit_request_amount = fields.Float(String="Credit request amount")
    limit_credit_aggregation = fields.Boolean("Limit credit aggregation")
    max_credit_amount = fields.Float("Maximum amount of credit allowed")

    def _prepare_credit_request_values(self, invoice):
        self.ensure_one()
        values = {
            "amount": self.credit_request_amount
            if self.different_credit_request_amount
            else invoice.amount_total,
            "partner_id": invoice.partner_id.id,
            "wallet_id": invoice.contract_id.wallet_id.id,
            "invoice_id": invoice.id,
            "no_order": True,
            "limit_credit_aggregation": self.limit_credit_aggregation,
            "max_credit_amount": self.max_credit_amount,
        }
        return values

    def _prepare_invoice(self, date_invoice, journal=None):
        invoice_vals = super()._prepare_invoice(date_invoice, journal)
        invoice_vals["contract_id"] = self.id
        return invoice_vals

    def _recurring_create_invoice(self, date_ref=False):
        invoices = super()._recurring_create_invoice(date_ref)
        for invoice in invoices:
            if (
                invoice.has_numeric_lcc_products
                and invoice.contract_id.create_credit_requests
            ):
                values = self._prepare_credit_request_values(invoice)
                self.env["credit.request"].create(values)
        return invoices
