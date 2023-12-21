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
                    partner = current_user.partner_id
                    to_add = partner._update_auth_data(
                        request.httprequest.authorization.password
                    )
                    lcc_profile_info = partner.lcc_profile_info()
                    if len(lcc_profile_info) == 0:
                        raise exceptions.UserError(
                            "Invalid User %r (id: %d), related partner %r (id: %d) has no public profile.",
                            current_user.login,
                            current_user.id,
                            partner.name,
                            partner.id,
                        )
                    response["prefetch"] = {
                        "backend_credentials": to_add,
                        "partner": lcc_profile_info[0],
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

    def signup(self):
        """Trigger odoo Sign-up process

        Note that we just forward the request to odoo's own entrypoint.

        Example request:
        {
          "login": "john.doe@email.com",
          "firstname": "John",
          "lastname": "Doe",
          "password": "p4ssw0rd",
        }
        """
        request.params["confirm_password"] = request.params["password"]
        web_auth_response = AuthSignupHome().web_auth_signup()
        error = web_auth_response.qcontext.get("error")
        if error:
            return {"error": error, "status": "Error"}
        return {"status": "OK"}

    def can_signup(self):
        """Return True if public sign-up is enabled"""
        return request.env["res.users"]._get_signup_invitation_scope() == "b2c"

    def can_reset_password(self):
        return (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("auth_signup.reset_password")
        ) == "True"

    def reset_password(self):
        """Request password reset email"""

        web_auth_response = AuthSignupHome().web_auth_reset_password()
        error = web_auth_response.qcontext.get("error")
        if error:
            return {"error": error, "status": "Error"}
        return {"status": "OK"}

    # Validator
    def _validator_authenticate(self):
        return {
            "db": {
                "type": "string",
            },
            "params": {"type": "list", "schema": {"type": "string"}},
        }

    def _validator_return_authenticate(self):
        return self.env["res.partner"]._validator_return_authenticate()

