import logging
from urllib.parse import unquote

from odoo.exceptions import AccessDenied, MissingError

from odoo.addons.component.core import Component

from odoo.addons.lcc_lokavaluto_app_connection.services import features, lcc_api

_logger = logging.getLogger(__name__)


class WalletService(Component):
    _inherit = "wallet.service"

    # Account types that require set_admin permission to assign.
    _ADMIN_ACCOUNT_TYPES = {2, 3, 4}

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

    def _archive_wallet(self, wallet):
        """Archive a comchain wallet with permission checks.

        Requires ``set_property`` or ``set_admin`` permission.
        Requires ``set_admin`` to archive admin-type wallets.
        Sets ``comchain_status`` to ``"inactive"`` before calling
        ``super()`` to set ``active = False``.
        """
        auth_data = self.env.comchain_caller_wallet.get_auth_context()
        perms = auth_data.get("comchain_perms", ())
        if "set_property" not in perms and "set_admin" not in perms:
            _logger.warning("archive denied: caller lacks set_property/set_admin")
            raise AccessDenied()
        current_type = int(wallet.comchain_type or "0")
        if current_type in self._ADMIN_ACCOUNT_TYPES and "set_admin" not in perms:
            _logger.warning(
                "archive denied: caller lacks set_admin for admin-type wallet "
                "(type %s)",
                current_type,
            )
            raise AccessDenied()
        wallet.sudo().comchain_status = "inactive"
        super()._archive_wallet(wallet)

    # -- Endpoints --

    @lcc_api(
        [(["/<wallet_ident>/auth_context"], "GET")],
        require_actions=True,
    )
    @features("wallet/0")
    def auth_context(self, wallet_ident):
        """Return auth context for a target wallet on the caller's currency."""
        wallet_ident = unquote(wallet_ident)
        target = self._resolve_target_wallet(wallet_ident)
        auth = target.get_auth_context()
        return sorted(auth.get("comchain_perms", ()))
