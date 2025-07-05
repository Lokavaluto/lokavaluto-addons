import logging

from odoo.http import request

from odoo.addons.component.core import Component
from odoo.addons.lcc_lokavaluto_app_connection.services.auth_services import AuthService

_logger = logging.getLogger(__name__)


class AuthService(Component):
    _inherit = "auth.service"

    def _update_auth_data(self, partner):
        data = super()._update_auth_data(partner)
        password = request.httprequest.authorization.password
        # Update cyclos password with odoo one from authenticate session
        for wallet_json_data in data:
            if not wallet_json_data["type"].startswith("cyclos"):
                continue
            if len(wallet_json_data["accounts"]) == 0:
                continue
            if len(wallet_json_data["accounts"]) > 1:
                raise("Multiple accounts for Cyclos not supported yet.")
            account = wallet_json_data["accounts"][0]
            wallet = self.env["res.partner.backend"].search(
                [
                    ("active", "=", True),
                    ("cyclos_id", "=", account["owner_id"]),
                ],
                limit=1,
            )
            if wallet:
                wallet.force_cyclos_password(password)
                new_token = wallet.cyclos_create_user_token(partner.id, password)
                if new_token:
                    account["token"] = new_token

        return data
