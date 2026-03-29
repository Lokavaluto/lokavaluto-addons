import logging
from urllib.parse import unquote

from odoo.exceptions import MissingError

from odoo.addons.component.core import Component

from . import features, lcc_api

_logger = logging.getLogger(__name__)


class WalletService(Component):
    _inherit = "base.rest.service"
    _name = "wallet.service"
    _usage = "wallet"
    _collection = "lokavaluto.private.services"
    _description = """Wallet Service — wallet management operations."""

    def _auth_user_uri(self, user_uri):
        """Authenticate caller from user URI. Override in backends.

        Called by the @lcc_api decorator to check if the caller has
        access to the entrypoint.

        Each backend overrides this to resolve the caller's wallet
        from the user URI, verify ownership, store whatever it needs
        on ``self.env``, and return the caller's authorized actions.

        Args:
            user_uri: value of the ``X-Lokapi-Caller-User-Uri`` header.

        Returns:
            list: authorized action strings. Empty in base.

        """
        return []

    def _get_caller_currency(self):
        """Return the currency of the authenticated caller.

        Override in backend add-ons.  Called after ``_auth_user_uri``
        has stored the caller wallet on ``self.env``.

        Returns:
            Single ``res.alt.currency`` record.

        Raises:
            odoo.exceptions.MissingError: always in base (no
                backend configured).
        """
        raise MissingError("No backend configured to identify caller currency")

    def _resolve_target_wallet(self, wallet_ident):
        """Resolve a non-archived wallet by ident on the caller's currency.

        Finds any wallet with ``active=True`` regardless of its
        backend-specific status (e.g. comchain ``disabled``).

        Args:
            wallet_ident: URL-decoded wallet identifier.

        Returns:
            Single ``res.partner.backend`` record.

        Raises:
            odoo.exceptions.MissingError: if no non-archived wallet
                matches the ident on the currency.
        """
        currency = self._get_caller_currency()
        target = self.env["res.partner.backend"].search(
            [
                ("alt_currency_id", "=", currency.id),
                ("active", "=", True),
                ("ident", "=", wallet_ident),
            ]
        )
        if not target:
            raise MissingError(
                f"Wallet '{wallet_ident}' not found on currency '{currency.ident}'"
            )
        return target

    def _archive_wallet(self, wallet):
        """Archive a wallet record.

        Sets ``active = False`` on the wallet.  Override in backend
        add-ons to also set backend-specific status fields before
        calling ``super()``.

        Args:
            wallet: single ``res.partner.backend`` record.
        """
        wallet.sudo().active = False

    # -- Endpoints --

    @lcc_api(
        [(["/<wallet_ident>/archive"], "POST")],
    )
    @features("wallet/0")
    def archive(self, wallet_ident):
        """Archive a wallet on the caller's currency."""
        wallet_ident = unquote(wallet_ident)
        target = self._resolve_target_wallet(wallet_ident)
        self._archive_wallet(target)
        return True
