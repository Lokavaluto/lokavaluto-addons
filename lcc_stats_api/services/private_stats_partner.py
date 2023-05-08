import logging

from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class PrivateStatsPartnerService(Component):
    _inherit = "base.rest.service"
    _name = "private_stats_partner.service"
    _usage = "partner"
    _collection = "lokavaluto.private.stats.services"
    _description = """
        MLCC Partner Private Stats Services
        Get private statistics of a local currency partner.
        Authentication: get a token using API /lokavaluto_api/public/auth/authenticate
    """

    # The following method are 'public' and can be called from the controller.

    @restapi.method(
        [(["/<int:id>/get", "/<int:id>"], "GET")],
        input_param=Datamodel("stats.filter"),
    )
    def get(self, _id, stats_filter):
        """
        Get a partner MLCC stats.
        """
        domain = [("partner_id", "=", _id)]
        invoices = self.env["account.invoice"].search(domain)
        print("got invoices")
        for invoice in invoices:
            print(invoice)
            print(invoice.type)

        print(invoices)
        return {"message": f"Hello {_id} and {invoices}"}
