import logging

from odoo.addons.component.core import Component
from odoo.addons.base_rest_datamodel.restapi import Datamodel

from . import features, lcc_api

_logger = logging.getLogger(__name__)


class RecipientService(Component):
    _inherit = "lcc.api.service"
    _name = "recipient.service"
    _usage = "recipient"
    _description = """Recipient Service — recipient search operations."""

    # -- Endpoints --

    @lcc_api(
        [(["/search_all"], "GET")],
        require_actions=("search-all-recipients",),
        input_param=Datamodel("partner.search.info"),
    )
    @features("recipient/0")
    def search_all(self, params):
        """Search all recipients (admin-only, no restriction rules)."""
        partner_service = self.work.component(usage="partner")
        return partner_service._search_recipients_common(
            backend_keys=params.backend_keys,
            value=params.value,
            offset=params.offset,
            limit=params.limit,
            order=params.order,
            website_url=params.website_url,
            extra_domain=[
                ("status", "not in", ["to_confirm"]),
            ],
        )
