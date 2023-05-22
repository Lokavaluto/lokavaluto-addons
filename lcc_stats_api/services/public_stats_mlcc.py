import logging

from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.component.core import Component

from .build_stats import (
    build_currency_stats_from_invoices,
    CurrencyStats,
    currency_stats_validator,
)
from ..datamodel.stats_filter import StatsFilter

_logger = logging.getLogger(__name__)


class MlccStats(CurrencyStats):
    nb_individuals: int
    nb_companies: int


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

        currency_stats: CurrencyStats = build_currency_stats_from_invoices(
            self.env["account.invoice"].sudo(), stats_filter=stats_filter
        )

        domain_partners = [
            ("membership_state", "!=", "none"),
            ("is_main_profile", "=", True),
        ]
        partners = self.env["res.partner"].sudo().search(domain_partners)
        for p in partners:
            print(f"partner {p.name} {p.is_company} {p.membership_state}")
        individuals = len([p for p in partners if p.is_company == False])
        companies = len(partners) - individuals
        return MlccStats(
            **currency_stats, nb_individuals=individuals, nb_companies=companies
        )

    ##########################################################
    # Validators
    ##########################################################
    def _validator_return_get(self):
        res = {
            **currency_stats_validator,
            "nb_individuals": {"type": "integer", "required": True, "empty": False},
            "nb_companies": {"type": "integer", "required": True, "empty": False},
        }
        return res
