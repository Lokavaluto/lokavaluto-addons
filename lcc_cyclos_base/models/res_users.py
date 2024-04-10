import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)

ALLOWED_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`@!\"#$%&'()*+,-./:;<=>?[\\]^_{}~"


def valid_password(password):
    return all(c in ALLOWED_CHARS for c in password)


class ResUsers(models.Model):
    """Inherits partner, adds Cyclos fields in the partner form, and functions"""

    _inherit = "res.users"

    def _set_password(self):
        for user in self:
            if valid_password(user.password):
                super(ResUsers, user)._set_password()
                continue
            raise UserError(
                _("Password must contain only the following characters: %s")
                % ALLOWED_CHARS
            )

    ## We need to override auth_signup logic here because, it
    ## invalidates the token before trying ``_set_password``
    @api.model
    def signup(self, values, token=None):
        if "password" in values:
            if not valid_password(values["password"]):
                raise UserError(
                    _("Password must contain only the following characters: %s")
                    % ALLOWED_CHARS
                )
        return super(ResUsers, self).signup(values, token)


    ## OAuth in cyclos needs some specific calls (that are not implemented)
    ## it requires:
    ##  - POST
    ##  - special header
    @api.model
    def _auth_oauth_rpc(self, endpoint, access_token):
        return requests.post(endpoint, headers={'Authorization': 'Bearer %s' % access_token}, timeout=10).json()

    ## Cyclos token is in 'token' not 'access_token'
    @api.model
    def auth_oauth(self, provider, params):
        if not params.get('access_token'):
            if params.get('token'):
                params['access_token'] = params['token']
        return super(ResUsers, self).auth_oauth(provider, params)

    ## Cyclos returns 'preferred_username' instead of 'user_id'
    @api.model
    def _auth_oauth_validate(self, provider, access_token):
        validation = super(ResUsers, self)._auth_oauth_validate(provider, access_token)
        if not validation.get('user_id') and validation.get('preferred_username'):
            validation['user_id'] = validation['preferred_username']
        return validation
