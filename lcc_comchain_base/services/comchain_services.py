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
        [(["/partners"], "POST")],
        input_param=Datamodel("comchain.partners.info"),
    )
    def partners(self, params):
        """
        Return display name for partner matching comchain addresses
        """
        partner = self.env.user.partner_id
        partner_ids = partner.search([("comchain_id", "in", params.addresses)])
        res = {}
        for partner in partner_ids:
            res[partner.comchain_id] = {
                "partner_id": partner.id,
                "display_name": partner.display_name,
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
        if not partner.comchain_wallet:
            res = partner.write(
                {
                    "comchain_id": params.address,
                    "comchain_wallet": params.wallet,
                    "comchain_message_key": params.message_key,
                }
            )
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
        partner = self.env["res.partner"]
        for account in params.accounts:
            partners = partner.search([("comchain_id", "=", account.address)])
            partners.activateComchainUser(account)

        return True
