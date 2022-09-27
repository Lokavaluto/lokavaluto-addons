from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)

ALLOWED_CHARS="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`@!\"#$%&'()*+,-./:;<=>?[\\]^_{}~"


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
            raise UserError(_('Password must contain only the following characters: %s') % ALLOWED_CHARS)

    ## We need to override auth_signup logic here because, it
    ## invalidates the token before trying ``_set_password``
    @api.model
    def signup(self, values, token=None):
        if "password" in values:
            if not valid_password(values["password"]):
                raise UserError(_('Password must contain only the following characters: %s') % ALLOWED_CHARS)
        return super(ResUsers, self).signup(values, token)

