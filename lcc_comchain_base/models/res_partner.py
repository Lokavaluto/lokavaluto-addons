from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Inherits partner:
    - add comchain fields in the partner form
    - add functions"""

    _inherit = "res.partner"

    def backends(self):
        self.ensure_one()
        backends = super(ResPartner, self).backends()
        wallets = self.get_wallets("comchain")
        if not wallets:
            return backends
        backend_id = wallets[0].comchain_backend_id
        if not backend_id:
            ## not present in wallet and not configured in general settings
            return backends
        return backends | {backend_id}

    def show_app_access_buttons(self):
        # For comchain the app access buttons on the portal are always displayed
        # as long as the comchain currency is defined,
        # as the user needs to connect to Monujo to create its wallet
        res = super(ResPartner, self).show_app_access_buttons()
        if self.env.user.company_id.comchain_currency_name:
            res = True
        return res
