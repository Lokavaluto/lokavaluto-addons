import logging

from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.component.core import Component

from ..datamodel.stats_filter import StatsFilter
from ..models.account_invoice import CurrencyStats

_logger = logging.getLogger(__name__)


class PrivateStatsPartnerService(Component):
    _inherit = "base.rest.service"
    _name = "private_stats_partner.service"
    _usage = "partner"
    _collection = "lokavaluto.private.stats.services"
    _description = """
        MLCC Partner Private Stats Services
        Get private statistics of a local currency partner.
    """

    @restapi.method(
        [(["/get", "/"], "GET")],
        input_param=Datamodel("stats.filter"),
    )
    def get(self, stats_filter: StatsFilter) -> CurrencyStats:
        """
        Get a partner MLCC stats.
        """

        # Get currency stats based on partner's invoices
        currency_stats: CurrencyStats = self.env["account.invoice"].get_mlcc_stats(
            stats_filter
        )

        return currency_stats

    ##########################################################
    # Swagger Validators
    ##########################################################

    # We override the Swagger method that will display params for this component's routes
    def _get_openapi_default_parameters(self):
        # For each private route in this class, we retrieve the params specified at route level
        defaults = super(
            PrivateStatsPartnerService, self
        )._get_openapi_default_parameters()
        # We append to existing params another one related to private endpoint: API-KEY
        defaults.append(
            {
                "name": "API-KEY",
                "in": "header",
                "description": "Auth API key - get a token using API /lokavaluto_api/public/auth/authenticate",
                "required": True,
                "schema": {"type": "string"},
                "style": "simple",
            }
        )

        return defaults
