import logging

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class WalletService(Component):
    _inherit = "wallet.service"

    def _update_wallet(self, wallet, vals):
        """Update not implemented for cyclos backends."""
        if wallet.type == "cyclos":
            raise NotImplementedError("update is not implemented for cyclos backends")
        super()._update_wallet(wallet, vals)

    def _archive_wallet(self, wallet):
        """Archive a cyclos wallet by setting cyclos_status."""
        if wallet.type == "cyclos":
            wallet.sudo().cyclos_status = "inactive"
        super()._archive_wallet(wallet)
