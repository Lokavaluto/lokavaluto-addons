from odoo import models, fields, api
from ..tools import status


class AccountInvoice(models.Model):
    _inherit = "account.move"

    has_numeric_lcc_products = fields.Boolean(
        string="Has lcc numeric products",
        compute="_compute_has_numeric_lcc_products",
        store=True,
    )
    credit_request_ids = fields.One2many(
        "credit.request", "invoice_id", string="Credit Requests"
    )
    global_credit_status = fields.Selection(
        [
            ("todo", "To do"),
            ("ongoing", "On going"),
            ("done", "Done"),
        ],
        string="Global Credit Status",
        compute="_compute_global_credit_status",
        tracking=True,
    )
    global_lcc_amount_credited = fields.Float(
        string="LCC amount credited", compute="_compute_global_lcc_amounts"
    )
    global_lcc_amount_to_credit = fields.Float(
        string="LCC amount to credit", compute="_compute_global_lcc_amounts"
    )

    @api.depends("credit_request_ids")
    def _compute_global_credit_status(self):
        self.global_credit_status = status(
            r.state == "done" for r in self.credit_request_ids
        )

    @api.depends("credit_request_ids")
    def _compute_global_lcc_amounts(self):
        done_requests = self.credit_request_ids.filtered(lambda x: x.state == "done")
        pending_requests = self.credit_request_ids.filtered(lambda x: x.state != "done")
        self.global_lcc_amount_credited = sum(done_requests.mapped("amount"))
        self.global_lcc_amount_to_credit = sum(pending_requests.mapped("amount"))

    @api.depends("state", "invoice_line_ids.product_id")
    def _compute_has_numeric_lcc_products(self):
        self.has_numeric_lcc_products = False
        try:
            categ = self.env.ref(
                "lcc_lokavaluto_app_connection.product_category_numeric_lcc"
            )
        except Exception as e:
            categ = self.env["product.category"].search([("name", "=", "Numeric LCC")])
        if categ:
            lcc_numeric_products = self.invoice_line_ids.filtered(
                lambda line: line.product_id.categ_id == categ
                or line.product_id.categ_id.parent_id == categ
            )
            if lcc_numeric_products:
                self.has_numeric_lcc_products = True

    def _invoice_paid_hook(self):
        res = super(AccountInvoice, self)._invoice_paid_hook()
        for invoice in self.filtered(
            lambda move: move.is_invoice()
            and move.is_sale_document()
            and move.has_numeric_lcc_products
        ):
            for request in invoice.credit_request_ids:
                # Only the opened request are concerned
                if request.state != "open":
                    continue
                # Set the state in "pending" to launch the top up process
                request.write({"state": "pending"})
        return res


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    @api.model_create_multi
    def create(self, vals_list):
        res = super(AccountInvoiceLine, self).create(vals_list)
        for record in res:
            for sale_line in record.sale_line_ids:
                if sale_line.order_id.credit_request_ids:
                    requests = sale_line.order_id.credit_request_ids
                    for request in requests:
                        request.invoice_id = record.move_id.id
        return res
