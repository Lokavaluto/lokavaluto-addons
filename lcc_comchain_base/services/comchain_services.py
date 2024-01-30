import logging
from werkzeug.exceptions import NotFound
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
            wallets = partner.get_wallets("comchain")
            for wallet in wallets:
                res[wallet.comchain_id] = {
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
        wallets = partner.get_wallets("comchain")
        if len(wallets) == 0:
            self.env["res.partner.backend"].sudo().create(
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
        wallet_obj = self.env["res.partner.backend"]
        for account in params.accounts:
            domain = [
                ("comchain_id", "=", account.address),
            ]
            if account.recipient_id:
                domain.append(("partner_id", "=", account.recipient_id))
            wallet_id = wallet_obj.search(domain, limit=2)
            if len(wallet_id) == 0:
                raise NotFound("Wallet %s not found in Odoo" % account.address)
            if len(wallet_id) > 1:
                raise NotImplementedError(
                    "Several wallets retrieved with same address. Please contact your administrator"
                )
            wallet_id.activate(account.type, account.credit_min, account.credit_max)
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
            # Retrieve the partner's wallet - Only one is expected to match the filter
            wallet_id = list(
                filter(
                    lambda x: x.comchain_id == comchain_address,
                    partner.get_wallets("comchain"),
                )
            )
            if len(wallet_id) == 0:
                raise NotFound("Wallet %s not found in Odoo" % comchain_address)
            data = {
                "wallet_id": wallet_id[0].id,
                "amount": amount,
                "create_order": True,
            }
            credit_request = self.env["credit.request"].sudo().create(data)
            comchain_response.order_url = (
                base_url + credit_request.order_id.get_portal_url()
            )
        return comchain_response
