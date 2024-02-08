import logging

from odoo.addons.component.core import Component
from odoo.addons.lcc_lokavaluto_app_connection.services.partner_services import (
    PartnerService,
)

_logger = logging.getLogger(__name__)


class PartnerService(Component):
    _inherit = "partner.service"

    def _update_search_data(self, partner, backend_keys):
        _logger.debug("SEARCH: backend_keys = %s" % backend_keys)
        data = super(PartnerService, self)._update_search_data(partner, backend_keys)
        wallets = partner.get_wallets("comchain")
        for wallet in wallets:
            if wallet.comchain_id:
                for backend_key in backend_keys:
                    if backend_key.startswith("comchain:"):
                        data[backend_key] = [wallet.comchain_id]
        _logger.debug("SEARCH: data %s" % data)
        return data

    def _get_backend_credentials(self, partner):
        data = super(PartnerService, self)._get_backend_credentials(partner)
        wallets = partner.get_wallets("comchain")
        if len(wallets) == 0:
            data.extend(self.env["res.partner.backend"].comchain_backend_accounts_data)
        for wallet in wallets:
            data.extend(wallet.comchain_backend_accounts_data)
        return data
