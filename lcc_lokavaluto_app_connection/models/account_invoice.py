from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    has_numeric_lcc_products = fields.Boolean(
        string="Has lcc numeric products",
        compute="_compute_has_numeric_lcc_products",
        store=True,
    )

    @api.one
    @api.depends("state", "invoice_line_ids.product_id")
    def _compute_has_numeric_lcc_products(self):
        self.has_numeric_lcc_products = False

        categ = self.env["product.category"].search([("name", "=", "Numeric LCC")])

        lcc_numeric_products = self.invoice_line_ids.filtered(
            lambda line: line.product_id.categ_id == categ
            or line.product_id.categ_id.parent_id == categ
        )
        if lcc_numeric_products:
            self.has_numeric_lcc_products = True

    def _get_credit_requests(self, backend_keys):
        ### This method should be inherited in backends modules.###
        return []

    def _validate_credit_request(self, invoice_ids):
        return []
