import logging

from odoo.addons.component.core import Component
from odoo.addons.lcc_lokavaluto_app_connection.services.auth_services import AuthService

_logger = logging.getLogger(__name__)


class AuthService(Component):
    _inherit = "auth.service"

    def _update_auth_data(self, partner, password):
        data = super(AuthService, self)._update_auth_data(partner, password)
        # Update cyclos password with odoo one from authenticate session
        wallets = partner.get_wallets("cyclos")
        if len(wallets) == 0:
            data.extend(self.env["res.partner.backend"].cyclos_backend_json_data)
        for wallet in wallets:
            wallet_json_data = wallet.cyclos_backend_json_data
            if wallet and wallet_json_data:
                wallet.force_cyclos_password(password)
                new_token = wallet.cyclos_create_user_token(partner.id, password)
                if new_token:
                    for ua in wallet_json_data[0]["accounts"]:
                        ua["token"] = new_token
            data.extend(wallet_json_data)
        return data
