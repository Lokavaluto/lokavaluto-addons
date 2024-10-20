from odoo import models, fields, api
import logging
from ..tools import status

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    has_numeric_lcc_products = fields.Boolean(
        string="Has lcc numeric products",
        compute="_compute_has_numeric_lcc_products",
        store=True,
    )
    credit_request_ids = fields.One2many(
        "credit.request", "order_id", string="Credit Requests"
    )
    global_credit_status = fields.Selection(
        [
            ("todo", "To do"),
            ("ongoing", "On going"),
            ("done", "Done"),
        ],
        string="Global Credit Status",
        compute="_compute_credit_request_data",
        track_visibility="always",
    )
    global_lcc_amount_credited = fields.Float(
        string="LCC amount credited", compute="_compute_credit_request_data"
    )
    global_lcc_amount_to_credit = fields.Float(
        string="LCC amount to credit", compute="_compute_credit_request_data"
    )

    @api.one
    @api.depends("state", "order_line.product_id")
    def _compute_has_numeric_lcc_products(self):
        self.has_numeric_lcc_products = False
        try:
            categ = self.env.ref(
                "lcc_lokavaluto_app_connection.product_category_numeric_lcc"
            )
        except Exception as e:
            categ = self.env["product.category"].search([("name", "=", "Numeric LCC")])
        if categ:
            lcc_numeric_products = self.order_line.filtered(
                lambda line: line.product_id.categ_id == categ
                or line.product_id.categ_id.parent_id == categ
            )
            if lcc_numeric_products:
                self.has_numeric_lcc_products = True

    @api.one
    @api.depends("credit_request_ids")
    def _compute_credit_request_data(self):
        if self.credit_request_ids:
            done_requests = self.credit_request_ids.filtered(lambda x: x.state == "done")
            pending_requests = self.credit_request_ids.filtered(lambda x: x.state != "done")
            self.global_lcc_amount_credited = sum(done_requests.mapped("amount"))
            self.global_lcc_amount_to_credit = sum(pending_requests.mapped("amount"))
            self.global_credit_status = status(
                r.state == "done" for r in self.credit_request_ids
            )
