from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

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
            ("to_do", "To do"),
            ("on_going", "On going"),
            ("done", "Done"),
        ],
        string="Global Credit Status",
        compute="_compute_global_credit_status",
        track_visibility="always",
    )
    global_lcc_amount_credited = fields.Float(
        string="LCC amount credited", compute="_compute_global_lcc_amounts"
    )
    global_lcc_amount_to_credit = fields.Float(
        string="LCC amount to credit", compute="_compute_global_lcc_amounts"
    )

    @api.one
    @api.depends("credit_request_ids")
    def _compute_global_credit_status(self):
        status = "to_do"
        for request in self.credit_request_ids:
            if request.state == "done":
                status = "done"
            elif request.state != "done" and status == "done":
                status = "on_going"
                break
        self.global_credit_status = status

    @api.one
    @api.depends("credit_request_ids")
    def _compute_global_lcc_amounts(self):
        done_requests = self.credit_request_ids.filtered(lambda x: x.state == "done")
        pending_requests = self.credit_request_ids.filtered(lambda x: x.state != "done")
        self.global_lcc_amount_credited = sum(done_requests.mapped("amount"))
        self.global_lcc_amount_to_credit = sum(pending_requests.mapped("amount"))

    @api.one
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

    @api.multi
    def action_invoice_paid(self):
        super(AccountInvoice, self).action_invoice_paid()
        for invoice in self:
            if (
                (invoice.type != "out_invoice")
                or (invoice.state != "paid")
                or not invoice.has_numeric_lcc_products
            ):
                # This invoice is not concerned by the top up process
                continue

            for request in invoice.credit_request_ids:
                # Only the opened request are concerned
                if request.state != "open":
                    continue
                # Set the state in "pending" to launch the top up process
                request.write({"state": "pending"})


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.model_create_multi
    def create(self, vals_list):
        res = super(AccountInvoiceLine, self).create(vals_list)
        for record in res:
            for sale_line in record.sale_line_ids:
                if sale_line.order_id.credit_request_ids:
                    requests = sale_line.order_id.credit_request_ids
                    for request in requests:
                        request.invoice_id = record.invoice_id.id
        return res
