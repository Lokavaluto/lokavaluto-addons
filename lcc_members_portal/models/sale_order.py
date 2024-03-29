from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def create_membership(self, vals):
        product_context = dict(self.env.context)
        product_context.setdefault("lang", self.sudo().partner_id.lang)
        SaleOrderLineSudo = (
            self.env["sale.order.line"].sudo().with_context(product_context)
        )
        product = False
        if vals.get("member_product_id", False):
            product = self.env["product.product"].search(
                [("product_tmpl_id", "=", vals.get("member_product_id"))]
            )

        if not product:
            raise UserError(
                _(
                    """The given combination does not exist therefore it cannot be added to cart. No membership product found !:
                    Please verify that membership product exist and is checked as 'use in portal'
                    """
                )
            )
        product_id = product.id
        values = {
            "product_id": product_id,
            "product_uom_qty": 1,
            "order_id": vals.get("order_id"),
            "product_uom": product.uom_id.id,
            "price_unit": vals.get("total_membership"),
        }

        order_line = SaleOrderLineSudo.create(values)
        order_line._compute_tax_id()
        return {"line_id": order_line.id, "quantity": 1, "option_ids": []}
