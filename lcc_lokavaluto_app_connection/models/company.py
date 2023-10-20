from odoo import models, fields


class Company(models.Model):
    _inherit = "res.company"

    monujo_web_app_url = fields.Char(string="Monujo web app URL")
    monujo_android_app_url = fields.Char(string="Monujo Android app URL")
    monujo_ios_app_url = fields.Char(string="Monujo iOS app URL")
    activate_automatic_topup = fields.Boolean('Activate Automatic Topup')
