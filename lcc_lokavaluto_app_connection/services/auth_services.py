
import logging
from odoo import exceptions
from odoo.http import request
from odoo.addons.base_rest.components.service import to_int
from odoo.addons.component.core import Component


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
        api_key_model = self.env['auth.api.key'].sudo()
        response = {'status': 'OK'}
        if request.httprequest.authorization and not request.session._login:
            try:
                uid = request.session.authenticate(
                    params.get('db'),
                    request.httprequest.authorization.username,
                    request.httprequest.authorization.password,
                    None
                )
                current_key = api_key_model.search([('user_id', '=', uid)], limit=1)
                current_user = self.env['res.users'].sudo().search([('id', '=', uid)])
                _logger.debug('USER: %s' % current_user)
                if current_user:
                    to_add = current_user.partner_id._update_auth_data(request.httprequest.authorization.password)
                    response.update(to_add)
                    _logger.debug("AUTH UPDATE to_add: %s" % to_add)
                    _logger.debug("AUTH UPDATE response: %s" % response)
                    response['partner_id'] = current_user.partner_id.id
                if not current_key:
                    current_key = api_key_model.create({
                        'user_id': uid,
                    })
                response['uid'] = uid
                response['api_token'] = "%s" % current_key.key
            except Exception as e:
                response['error'] = "%s" % e
                response['status'] = "Error"
        return {"response": response}


    # Validator
    def _validator_authenticate(self):
        return {
            "db": {"type": "string", "required": True},
            "params": {"type": "list", "schema": {"type": "string"}},
        }

    def _validator_return_authenticate(self):
        return self.env['res.partner']._validator_return_authenticate()
