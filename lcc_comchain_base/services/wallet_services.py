import logging
from urllib.parse import unquote

from odoo.exceptions import AccessDenied, ValidationError

from odoo.addons.component.core import Component

from odoo.addons.lcc_lokavaluto_app_connection.services import features, lcc_api

_logger = logging.getLogger(__name__)


class WalletService(Component):
    _inherit = "wallet.service"

    # -- Account type mapping (comchain-specific) --
    # Valid comchain account type integers.
    _VALID_ACCOUNT_TYPES = {0, 1, 2, 3, 4}

    # Valid comchain status values.
    _VALID_COMCHAIN_STATUSES = {"active", "pending", "blocked", "disabled"}

    # Account types that require set_admin permission to assign.
    _ADMIN_ACCOUNT_TYPES = {2, 3, 4}

    def _update_wallet(self, wallet, vals):
        """Update a comchain wallet with permission checks and validation.

        Requires ``set_property`` or ``set_admin`` for any change.
        Requires ``set_admin`` to promote/demote admin types or
        change status on admin-type wallets.
        """
        if wallet.type != "comchain":
            return super()._update_wallet(wallet, vals)

        auth_data = self.env.comchain_caller_wallet.get_auth_context()
        perms = auth_data.get("comchain_perms", ())

        # Require set_property or set_admin for any change
        if "set_property" not in perms and "set_admin" not in perms:
            _logger.warning("update denied: caller lacks set_property/set_admin")
            raise AccessDenied()

        current_type = int(wallet.comchain_type or "0")
        status = vals.get("status")
        account_type = vals.get("accountType")
        low_limit = vals.get("lowLimit")
        high_limit = vals.get("highLimit")

        # Changing status on an admin account requires set_admin
        if status is not None and current_type in self._ADMIN_ACCOUNT_TYPES:
            if "set_admin" not in perms:
                _logger.warning(
                    "update denied: caller lacks set_admin to change status "
                    "on admin-type wallet (type %s)",
                    current_type,
                )
                raise AccessDenied()

        # Validate and apply account type
        account_type_int = None
        if account_type is not None:
            if not isinstance(account_type, int):
                raise ValidationError(
                    f"accountType must be an integer, "
                    f"got: {type(account_type).__name__}"
                )
            if account_type not in self._VALID_ACCOUNT_TYPES:
                raise ValidationError(f"Unknown account type: {account_type}")
            account_type_int = account_type

            # Require set_admin to promote TO or demote FROM admin types
            needs_admin = (
                account_type_int in self._ADMIN_ACCOUNT_TYPES
                or current_type in self._ADMIN_ACCOUNT_TYPES
            )
            if needs_admin and "set_admin" not in perms:
                _logger.warning(
                    "update denied: caller lacks set_admin for type change %s -> %s",
                    current_type,
                    account_type_int,
                )
                raise AccessDenied()

        # Write comchain-specific fields
        write_vals = {}
        if account_type_int is not None:
            write_vals["comchain_type"] = str(account_type_int)
        if low_limit is not None:
            write_vals["comchain_credit_min"] = low_limit
        if high_limit is not None:
            write_vals["comchain_credit_max"] = high_limit
        if write_vals:
            wallet.sudo().write(write_vals)

        # Write comchain status
        if status is not None:
            if status not in self._VALID_COMCHAIN_STATUSES:
                raise ValidationError(
                    f"Invalid status: '{status}'. "
                    f"Must be one of: {', '.join(sorted(self._VALID_COMCHAIN_STATUSES))}"
                )
            wallet.sudo().comchain_status = status

    def _archive_wallet(self, wallet):
        """Archive a comchain wallet with permission checks.

        Requires ``set_property`` or ``set_admin`` permission.
        Requires ``set_admin`` to archive admin-type wallets.
        Sets ``comchain_status`` to ``"disabled"`` before calling
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
        ## Client is supposed to call this entrypoint after setting
        ## status to "disabled" on the comchain side
        wallet.sudo().comchain_status = "disabled"
        super()._archive_wallet(wallet)

    def _get_wallet(self, wallet):
        """Add comchain permission check before returning wallet data.

        Requires ``set_property`` or ``set_admin`` permission.
        """
        auth_data = self.env.comchain_caller_wallet.get_auth_context()
        perms = auth_data.get("comchain_perms", ())
        if "set_property" not in perms and "set_admin" not in perms:
            _logger.warning("get denied: caller lacks set_property/set_admin")
            raise AccessDenied()
        return super()._get_wallet(wallet)

    # -- Endpoints --

    @lcc_api(
        [(["/<wallet_ident>/get"], "GET")],
        require_actions=True,
    )
    @features("wallet/0")
    def get(self, wallet_ident):
        """Return wallet JSON data with comchain permission check."""
        return super().get(wallet_ident)

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
