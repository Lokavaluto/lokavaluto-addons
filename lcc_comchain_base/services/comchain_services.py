import logging

from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class ComchainService(Component):
    _inherit = "base.rest.service"
    _name = "comchain.service"
    _usage = "comchain"
    _collection = "lokavaluto.private.services"
    _description = """
        Comchain Services
        Access to the Comchain services is allowed to everyone connected
    """

    @restapi.method(
        [(["/contact"], "POST")],
        input_param=Datamodel("comchain.partners.info"),
    )
    def contact(self, params):
        """Return public name for contacts matching comchain addresses"""
        partner = self.env["res.partner"]
        partner_ids = partner.search(
            [("lcc_backend_ids.comchain_id", "in", params.addresses)]
        )
        res = {}
        for partner in partner_ids:
            backend_data = partner.get_wallet("comchain")
            res[backend_data.comchain_id] = {
                "partner_id": partner.id,
                "public_name": partner.public_name,
            }
        return res

    @restapi.method(
        [(["/register"], "POST")],
        input_param=Datamodel("comchain.register.info"),
    )
    def register(self, params):
        """
        Add comchain account details on partner
        """
        partner = self.env.user.partner_id
        backend_data = partner.get_wallet("comchain")
        if not backend_data.comchain_wallet:
            backend_data.create(
                {
                    "type": "comchain",
                    "name": "comchain:%s" % params.address,
                    "partner_id": partner.id,
                    "comchain_status": "pending",
                    "comchain_id": params.address,
                    "comchain_wallet": params.wallet,
                    "comchain_message_key": params.message_key,
                }
            )
            res = True
        else:
            res = {
                "error": "account already exist",
                "status": "Error",
            }
        return res

    @restapi.method(
        [(["/activate"], "POST")],
        input_param=Datamodel("comchain.activate.list"),
    )
    def activate(self, params):
        """
        Activate comchain account on partners

        """
        partner_obj = self.env["res.partner"]
        for account in params.accounts:
            partner_id = partner_obj.search(
                [("lcc_backend_ids.comchain_id", "=", account.address)]
            )
            partner_id.activate_comchain_user(account)

        return True

    @restapi.method(
        [(["/credit"], "POST")],
        input_param=Datamodel("comchain.credit.info"),
        output_param=Datamodel("comchain.credit.response"),
    )
    def credit(self, params):
        """Credit user account with amount and generate accounting entry"""
        partner = self.env.user.partner_id
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        _logger.debug("PARTNER ?: %s(%s)" % (partner.name, partner.id))
        comchain_address = params.comchain_address
        amount = params.amount
        comchainCreditResponse = self.env.datamodels["comchain.credit.response"]
        comchain_response = comchainCreditResponse(partial=True)
        if comchain_address and amount:
            new_order = partner.comchain_create_order(comchain_address, amount)
            comchain_response.order_url = base_url + new_order.get_portal_url()
        return comchain_response
