import logging

from odoo.addons.component.core import Component
from odoo.addons.lcc_lokavaluto_app_connection.services.partner_services import (
    PartnerService,
)

_logger = logging.getLogger(__name__)


class PartnerService(Component):
    _inherit = "partner.service"

    def _update_search_data(self, partner, backend_keys):
        data = super(PartnerService, self)._update_search_data(partner, backend_keys)
        wallets = partner.get_wallets("cyclos")
        for wallet in wallets:
            for backend_key in backend_keys:
                if backend_key.startswith("cyclos:") and wallet.cyclos_id:
                    data[backend_key] = [wallet.cyclos_id]
        return data

    def _get_backend_credentials(self, partner):
        data = super(PartnerService, self)._get_backend_credentials(partner)
        wallets = partner.get_wallets("cyclos")
        if len(wallets) == 0:
            data.extend(self.env["res.partner.backend"].cyclos_backend_json_data)
        for wallet in wallets:
            data.extend(wallet.cyclos_backend_json_data)
        return data
