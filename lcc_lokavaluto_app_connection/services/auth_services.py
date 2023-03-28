import logging
from odoo import exceptions
from odoo.http import request
from odoo.addons.base_rest.components.service import to_int
from odoo.addons.lcc_members_portal.controllers.auth_signup import AuthSignupHome
from odoo.addons.component.core import Component
from .. import http

_logger = logging.getLogger(__name__)


class AuthService(Component):
    _inherit = "base.rest.service"
    _name = "auth.service"
    _usage = "auth"
    _collection = "lokavaluto.public.services"
    _description = """
        Ath Services
        Access to the Auth services is allowed to everyone
    """

    # The following method are 'public' and can be called from the controller.
    def authenticate(self, **params):
        """
        This method is used to authenticate and get the token for the user on mobile app.
        """
        api_key_model = self.env["auth.api.key"].sudo()
        response = {"status": "OK"}
        if request.httprequest.authorization and not request.session._login:
            try:
                uid = request.session.authenticate(
                    params.get("db") or self.env.cr.dbname,
                    request.httprequest.authorization.username,
                    request.httprequest.authorization.password,
                    None,
                )
                current_key = api_key_model.search([("user_id", "=", uid)], limit=1)
                current_user = self.env["res.users"].sudo().search([("id", "=", uid)])
                _logger.debug("USER: %s" % current_user)
                if current_user:
                    parser = self._get_partner_parser()
                    partner = current_user.partner_id
                    to_add = current_user.partner_id._update_auth_data(
                        request.httprequest.authorization.password
                    )
                    response["prefetch"] = {
                        "backend_credentials": to_add,
                        "partner": partner.jsonify(parser)[0],
                    }
                    if to_add:
                        response["monujo_backends"] = to_add
                    _logger.debug("AUTH UPDATE to_add: %s" % to_add)
                    _logger.debug("AUTH UPDATE response: %s" % response)
                if not current_key:
                    current_key = api_key_model.create(
                        {
                            "user_id": uid,
                        }
                    )
                response["uid"] = uid
                response["api_token"] = "%s" % current_key.key
                from . import __api_version__

                response["api_version"] = __api_version__
            except Exception as e:
                _logger.debug(http.format_last_exception())
                response["error"] = "%s" % e
                response["status"] = "Error"
        return response

    def can_reset_password(self):
        return (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("auth_signup.reset_password")
        ) == "True"

    def signup(self):
        """{
        "login": "test",
        "firstname": "test",
        "lastname": "test",
        "password": "a",
        "confirm_password": "a"
        }"""
        web_auth_response = AuthSignupHome().web_auth_signup()
        error = web_auth_response.qcontext.get("error")
        if error:
            return {"error": error, "status": "Error"}
        return {"status": "OK"}

    def reset_password(self):
        """Request password reset email"""

        web_auth_response = AuthSignupHome().web_auth_reset_password()
        error = web_auth_response.qcontext.get("error")
        if error:
            return {
                'error': error,
                'status': 'Error'
            }
        return {"status": "OK"}

    # Validator
    def _validator_authenticate(self):
        return {
            "db": {"type": "string", },
            "params": {"type": "list", "schema": {"type": "string"}},
        }

    def _validator_return_authenticate(self):
        return self.env["res.partner"]._validator_return_authenticate()

    def _get_partner_parser(self):
        parser = [
            "id",
            "name",
            "street",
            "street2",
            "zip",
            "city",
            "mobile",
            "email",
            "phone",
            "is_favorite",
            "is_company",
            "qr_url",
            ("country_id", ["id", "name"]),
            # ('state', ['id','name'])
        ]
        return parser
