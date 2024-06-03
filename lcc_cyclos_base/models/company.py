import re
from urllib.parse import urlparse
from werkzeug.exceptions import NotFound
from odoo import models, fields


class Company(models.Model):
    _inherit = "res.company"

    cyclos_server_url = fields.Char(string="Url for cyclos server")
    cyclos_client_token = fields.Char(string="Client token auth for cyclos server")

    cyclos_server_login = fields.Char(string="Login for cyclos server")

    cyclos_server_password = fields.Char(string="Password for cyclos server")

    def get_cyclos_server_domain(self):
        self.ensure_one()
        url = self.cyclos_server_url
        if not url:
            raise NotFound("Cyclos URL in Odoo configuration is empty")
        parsed_uri = urlparse(url)
        if not parsed_uri or not parsed_uri.netloc:
            raise SyntaxError(
                "Cyclos URL %r in Odoo configuration is not a valid url"
                % url
            )
        if not re.search("^[a-z0-9-]+(\.[a-z0-9-]+)*(:[0-9]+)?$", parsed_uri.netloc.lower()):
            raise SyntaxError(
                "domain %r in Odoo URL %r configuration is not valid"
                % (parsed_uri.netloc, url)
            )
        return parsed_uri.netloc
