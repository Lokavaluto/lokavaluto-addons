from odoo import models, fields


class Company(models.Model):
    _inherit = "res.company"

    comchain_server_url = fields.Char(
        string='Url for comchain server'
    )
