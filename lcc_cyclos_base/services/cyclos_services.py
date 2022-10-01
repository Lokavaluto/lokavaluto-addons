import logging
from odoo.addons.base_rest import restapi
from odoo.addons.base_rest.components.service import to_int
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class CyclosService(Component):
    _inherit = "base.rest.service"
    _name = "cyclos.service"
    _usage = "cyclos"
    _collection = "lokavaluto.private.services"
    _description = """
        Ping Services
        Access to the ping services is allowed to everyone
    """

    @restapi.method(
        [(["/credit"], "POST")],
        input_param=Datamodel("cyclos.credit.info"),
        output_param=Datamodel("cyclos.credit.response"),
    )
    def credit(self, params):
        """
        Credit user account with amount, and generate accounting entry
        """
        partner = self.env.user.partner_id
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        _logger.debug("PARTNER ?: %s(%s)" % (partner.name, partner.id))
        owner_id = params.owner_id
        amount = params.amount
        CyclosCreditResponse = self.env.datamodels["cyclos.credit.response"]
        cyclos_response = CyclosCreditResponse(partial=True)
        if owner_id and amount:
            new_order = partner.cyclosCreateOrder(owner_id, amount)
            cyclos_response.order_url = base_url + new_order.get_portal_url()
        return cyclos_response

    @restapi.method(
        [(["/contact"], "POST")],
        input_param=Datamodel("cyclos.partners.info"),
    )
    def contact(self, params):
        """Return public name for contact matching comchain addresses"""

        partner = self.env["res.partner"]
        partner_ids = partner.search(
            [("lcc_backend_ids.cyclos_id", "in", params.addresses)]
        )
        res = {}
        for partner in partner_ids:
            backend_data = partner._cyclos_backend()
            res[backend_data.cyclos_id] = {
                "partner_id": partner.id,
                "public_name": partner.public_name,
            }
        return res
