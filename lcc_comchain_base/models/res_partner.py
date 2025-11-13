import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Inherits partner:
    - add comchain fields in the partner form
    - add functions"""

    _inherit = "res.partner"

    def backends(self):
        self.ensure_one()
        backends = super().backends()
        wallets = self.get_wallets_by_currency_type("comchain")
        if not wallets:
            return backends
        for wallet in wallets:
            backends |= f"comchain:{wallet.alt_currency_id.ident}"
        return backends

    def show_app_access_buttons(self):
        # For comchain the app access buttons on the portal are always displayed
        # as long as the comchain currency is defined,
        # as the user needs to connect to Monujo to create its wallet
        res = super().show_app_access_buttons()
        if self.env["res.alt.currency"].search(
            [("active", "=", True), ("engine", "=", "comchain")]
        ):
            res = True
        return res
