import logging
from urllib.parse import unquote

from odoo.exceptions import MissingError

from odoo.addons.component.core import Component
from odoo.addons.base_rest_datamodel.restapi import Datamodel

from . import features, lcc_api

_logger = logging.getLogger(__name__)


class WalletService(Component):
    _inherit = "lcc.api.service"
    _name = "wallet.service"
    _usage = "wallet"
    _description = """Wallet Service — wallet management operations."""

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

    def _update_wallet(self, wallet, vals):
        """Update a wallet record with the given values.

        Override in backend add-ons to validate, permission-check,
        and apply backend-specific fields.  Base is a no-op.

        Args:
            wallet: single ``res.partner.backend`` record.
            vals: dict of API-level field values from the request body.
        """

    def _archive_wallet(self, wallet):
        """Archive a wallet record.

        Sets ``active = False`` on the wallet.  Override in backend
        add-ons to also set backend-specific status fields before
        calling ``super()``.

        Args:
            wallet: single ``res.partner.backend`` record.
        """
        wallet.sudo().active = False

    def _get_wallet(self, wallet):
        """Return wallet account data from a resolved wallet record.

        Fetches JSON data via ``get_wallet_json_data()`` and extracts
        the single account entry.  Override in backend add-ons to add
        permission checks before calling ``super()``.

        Args:
            wallet: single ``res.partner.backend`` record.

        Returns:
            dict with the single account data.

        Raises:
            odoo.exceptions.MissingError: if accounts data is missing
                or has an unexpected number of entries.
        """
        data = wallet.get_wallet_json_data()
        if "accounts" not in data:
            raise MissingError("Wallet data should contain an 'accounts' field")
        if len(data["accounts"]) == 0:
            raise MissingError("Wallet has no account data")
        if len(data["accounts"]) > 1:
            raise MissingError(
                "Wallet has more than one account data, which is not supported"
            )
        return data["accounts"][0]

    # -- Endpoints --

    @lcc_api(
        [(["/<wallet_ident>/get"], "GET")],
        require_actions=True,
    )
    @features("wallet/0")
    def get(self, wallet_ident):
        """Return wallet JSON data for a target wallet."""
        wallet_ident = unquote(wallet_ident)
        target = self._resolve_target_wallet(wallet_ident)
        return self._get_wallet(target)

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

    @lcc_api(
        [(["/archived"], "GET")],
        require_actions=True,
    )
    @features("wallet/0")
    def archived(self):
        """Return list of archived wallet idents on the caller's currency."""
        currency = self._get_caller_currency()
        wallets = (
            self.env["res.partner.backend"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [
                    ("alt_currency_id", "=", currency.id),
                    ("active", "=", False),
                ]
            )
        )
        return list({w.ident for w in wallets if w.ident})

    @lcc_api(
        [(["/<wallet_ident>/update"], "POST")],
        input_param=Datamodel("wallet.update"),
    )
    @features("wallet/0")
    def update(self, wallet_ident, params):
        """Update a wallet on the caller's currency."""
        wallet_ident = unquote(wallet_ident)
        target = self._resolve_target_wallet(wallet_ident)
        self._update_wallet(target, params.data)
        return True
