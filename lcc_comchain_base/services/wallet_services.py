import logging
from urllib.parse import unquote

from odoo.exceptions import AccessDenied, MissingError

from odoo.addons.component.core import Component

from odoo.addons.lcc_lokavaluto_app_connection.services import features, lcc_api

_logger = logging.getLogger(__name__)


class WalletService(Component):
    _inherit = "wallet.service"

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

    # -- Endpoints --

    @lcc_api(
        [(["/<wallet_ident>/auth_context"], "GET")],
        require_actions=True,
    )
    @features("wallet/0")
    def auth_context(self, wallet_ident):
        """Return auth context for a target wallet on the caller's currency."""
        caller = self.env.comchain_caller_wallet
        currency = caller.alt_currency_id
        wallet_ident = unquote(wallet_ident)
        target = currency._search_active_wallets([("ident", "=", wallet_ident)])
        if not target:
            raise MissingError(
                f"Wallet '{wallet_ident}' not found on currency '{currency.ident}'"
            )
        auth = target.get_auth_context()
        return sorted(auth.get("comchain_perms", ()))
