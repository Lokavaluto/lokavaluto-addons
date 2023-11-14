from odoo import models, fields


class Company(models.Model):
    _inherit = "res.company"

    cyclos_server_url = fields.Char(string="Url for cyclos server")
    cyclos_client_token = fields.Char(string="Client token auth for cyclos server")

    cyclos_server_login = fields.Char(string="Login for cyclos server")

    cyclos_server_password = fields.Char(string="Password for cyclos server")

    def get_cyclos_server_domain(self):
        self.ensure_one()
        domain_url = self.cyclos_server_url
        remove = ["https://", "http://", "/api"]
        for value in remove:
            domain_url = domain_url.replace(value, "")
        return domain_url
