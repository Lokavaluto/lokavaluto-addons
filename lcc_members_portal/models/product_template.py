from datetime import datetime
from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    portal_private_registration_product = fields.Boolean(
        "Use for portal private registration",
    )
    portal_organization_registration_product = fields.Boolean(
        "Use for portal organization registration",
    )
    dynamic_price = fields.Boolean(
        "Use dynamic price ?",
    )

    @api.multi
    def get_private_membership_product(self, company_id):
        today = datetime.today()
        product_template = self.env["product.template"].search(
            [
                ("portal_private_registration_product", "=", True),
                ("portal_organization_registration_product", "=", False),
                ("active", "=", True),
                ("membership_date_from", "<=", today),
                ("membership_date_to", ">=", today),
                ("company_id", "=", company_id),
            ],
            limit=1,
        )
        return product_template

    @api.multi
    def get_organization_membership_product(self, company_id):
        today = datetime.today()
        product_template = self.env["product.template"].search(
            [
                ("portal_private_registration_product", "=", False),
                ("portal_organization_registration_product", "=", True),
                ("active", "=", True),
                ("membership_date_from", "<=", today),
                ("membership_date_to", ">=", today),
                ("company_id", "=", company_id),
            ],
            limit=1,
        )
        return product_template
