import logging

from odoo.addons.component.core import Component
from odoo.addons.lcc_lokavaluto_app_connection.services.auth_services import AuthService

_logger = logging.getLogger(__name__)


class AuthService(Component):
    _inherit = "auth.service"

    def _update_auth_data(self, partner, password):
        data = super(AuthService, self)._update_auth_data(partner, password)
        wallets = partner.get_wallets("comchain")
        if len(wallets) == 0:
            data.extend(self.env["res.partner.backend"].comchain_backend_accounts_data)
        for wallet in wallets:
            data.extend(wallet.comchain_backend_accounts_data)
        return data
