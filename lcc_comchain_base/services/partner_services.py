import logging

from odoo.addons.component.core import Component
from odoo.addons.lcc_lokavaluto_app_connection.services.partner_services import (
    PartnerService,
)

_logger = logging.getLogger(__name__)


class PartnerService(Component):
    _inherit = "partner.service"

    def _get_backend_credentials(self, partner):
        data = super(PartnerService, self)._get_backend_credentials(partner)
        wallets = partner.get_wallets("comchain")
        if len(wallets) == 0:
            data.extend(self.env["res.partner.backend"].comchain_backend_accounts_data)
        for wallet in wallets:
            data.extend(wallet.comchain_backend_accounts_data)
        return data
