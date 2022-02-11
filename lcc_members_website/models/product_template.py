from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    online_membership = fields.Boolean(
        "Use for online membership ?",
    )
    dynamic_price = fields.Boolean(
        "Use dynamic price ?",
    )

    @api.multi
    def get_web_member_products(self, is_company):
        if is_company is True:
            product_templates = self.env["product.template"].search(
                [
                    ("online_membership", "=", True),
                ]
            )
        else:
            product_templates = self.env["product.template"].search(
                [
                    ("online_membership", "=", True),
                ]
            )
        return product_templates
