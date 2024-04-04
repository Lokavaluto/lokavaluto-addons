from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    monujo_web_app_url = fields.Char(
        related="company_id.monujo_web_app_url",
        readonly=False,
        string="Monujo web app URL",
    )

    monujo_android_app_url = fields.Char(
        related="company_id.monujo_android_app_url",
        readonly=False,
        string="Monujo Android app URL",
    )

    monujo_ios_app_url = fields.Char(
        related="company_id.monujo_ios_app_url",
        readonly=False,
        string="Monujo iOS app URL",
    )

    activate_automatic_topup = fields.Boolean(
        related="company_id.activate_automatic_topup",
        readonly=False,
        string="Activate Automatic Topup",
    )
