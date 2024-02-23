import logging

from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.component.core import Component

from ..datamodel.stats_filter import StatsFilter
from ..models.account_invoice import CurrencyStats
from ..models.res_partner import PartnersStats

_logger = logging.getLogger(__name__)


class MlccStats(CurrencyStats, PartnersStats):
    pass


class PublicStatsMlccService(Component):
    _inherit = "base.rest.service"
    _name = "public_stats.service"
    _usage = "mlcc"
    _collection = "lokavaluto.public.stats.services"
    _description = """
        MLCC Public Stats Services
        Get public statistics about a local currency 
    """

    # The following method are 'public' and can be called from the controller.

    @restapi.method(
        [(["/get", "/"], "GET")],
        input_param=Datamodel("stats.filter"),
    )
    def get(self, stats_filter: StatsFilter) -> MlccStats:
        """
        Get MLCC public stats.
        """

        # Get currency stats based on all invoices
        currency_stats: CurrencyStats = (
            self.env["account.invoice"].sudo().get_mlcc_stats(stats_filter)
        )

        # Get partners stats
        partner_stats: PartnersStats = self.env["res.partner"].sudo().get_mlcc_stats()

        return MlccStats(**currency_stats, **partner_stats)
