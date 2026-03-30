import logging
from urllib.parse import unquote

from odoo.exceptions import AccessDenied, MissingError

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class LccApiService(Component):
    _inherit = "lcc.api.service"

    def _auth_user_uri(self, user_uri):
        """Comchain caller authentication from user URI.

        Converts the user URI to a wallet URI (comchain user ident
        is the wallet ident), resolves it, verifies ownership, stores
        the caller wallet on ``self.env.comchain_caller_wallet``, and
        returns authorized actions.
        """
        wallet_uri = unquote(user_uri.replace("/user/", "/wallet/", 1))
        try:
            wallet = self.env["res.partner.backend"].get_by_uri(wallet_uri)
        except MissingError:
            _logger.debug(
                "comchain _auth_user_uri: no wallet for URI '%s'",
                user_uri,
            )
            raise AccessDenied()

        if wallet.partner_id != self.env.user.partner_id:
            _logger.debug(
                "comchain _auth_user_uri: user '%s' does not own wallet '%s'",
                self.env.user.login,
                wallet_uri,
            )
            raise AccessDenied()

        self.env.comchain_caller_wallet = wallet
        return wallet.get_authorized_actions()

    def _get_caller_currency(self):
        """Return the currency from the comchain caller wallet."""
        return self.env.comchain_caller_wallet.alt_currency_id
