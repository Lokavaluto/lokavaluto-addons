import logging

from odoo.exceptions import AccessError
from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.component.core import Component
from odoo.http import request

from .build_stats import (
    CurrencyStats,
    build_currency_stats_from_invoices,
    currency_stats_validator,
)
from ..datamodel.stats_filter import StatsFilter

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

    # The following method are 'public' and can be called from the controller.

    @restapi.method(
        [(["/<int:id>/get", "/<int:id>"], "GET")],
        input_param=Datamodel("stats.filter"),
    )
    def get(self, _id, stats_filter: StatsFilter) -> CurrencyStats:
        """
        Get a partner MLCC stats.
        """

        # Check that user is accessing its own data
        user_api_key = request.httprequest.headers["Api-Key"]
        user = (
            self.env["auth.api.key"]
            .sudo()
            .search([("key", "=", user_api_key)], limit=1)
        )
        partner = (
            self.env["res.partner"]
            .sudo()
            .search([("odoo_user_id", "=", user.user_id.id)])
        )
        if _id != partner.id and _id != partner.public_profile_id.id:
            raise AccessError(
                f"{partner.name} not allowed to access data of partner ID {_id}"
            )

        currency_stats: CurrencyStats = build_currency_stats_from_invoices(
            self.env["account.invoice"], partner_id=_id, stats_filter=stats_filter
        )

        return currency_stats

    ##########################################################
    # Validators
    ##########################################################
    def _validator_return_get(self):
        res = {
            **currency_stats_validator,
        }
        return res

    def _get_openapi_default_parameters(self):
        defaults = super(
            PrivateStatsPartnerService, self
        )._get_openapi_default_parameters()
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
