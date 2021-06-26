from odoo import models, fields


class Company(models.Model):
    _inherit = "res.company"

    cyclos_server_url = fields.Char(
        string='Url for cyclos server'
    )
    cyclos_client_token = fields.Char(
        string='Client token auth for cyclos server'
    )

    cyclos_server_login = fields.Char(
        string='Login for cyclos server'
    )

    cyclos_server_password = fields.Char(
        string='Password for cyclos server'
    )
