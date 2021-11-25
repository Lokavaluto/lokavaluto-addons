from odoo import models, fields


class Company(models.Model):
    _inherit = "res.company"

    comchain_server_url = fields.Char(
        string='Url for comchain server'
    )

    comchain_currency_name = fields.Char(
        string='Currency name'
    )
