from odoo import models, fields, api


class Company(models.Model):
    _inherit = "res.company"

    @api.model
    def _default_digital_currency_product(self):
        return self.env.ref["lcc_lokavaluto_app_connection.product_product_numeric_lcc"]

    monujo_web_app_url = fields.Char(string="Monujo web app URL")
    monujo_android_app_url = fields.Char(string="Monujo Android app URL")
    monujo_ios_app_url = fields.Char(string="Monujo iOS app URL")
    activate_automatic_topup = fields.Boolean("Activate Automatic Topup")
    digital_currency_product_id = fields.Many2one("product.product", string="Digital Currency Product", default=_default_digital_currency_product)
