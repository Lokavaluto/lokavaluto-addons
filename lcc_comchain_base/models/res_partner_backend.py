import json
import logging
import re
from odoo import models, fields, api
from pyc3l import Pyc3l
from odoo.addons.lcc_lokavaluto_app_connection import http

pyc3l = Pyc3l()
_logger = logging.getLogger(__name__)


class ResPartnerBackend(models.Model):
    """Add backend commom property for local currency"""

    _inherit = "res.partner.backend"

    type = fields.Selection(selection_add=[("comchain", "Comchain")])
    comchain_id = fields.Char(string="Address")
    comchain_wallet = fields.Text(string="Crypted json wallet")
    comchain_status = fields.Char(string="Comchain Status")
    comchain_type = fields.Selection(
        [("0", "Personal"), ("1", "Company"), ("2", "Admin")],
        string="Type",
    )
    comchain_credit_min = fields.Float(string="Min Credit limit")
    comchain_credit_max = fields.Float(string="Max Credit limit")
    comchain_message_key = fields.Char(string="Message keys")

    @property
    def comchain_wallet_parsed(self):
        return json.loads(self.comchain_wallet) if self.comchain_wallet else {}

    @property
    def comchain_backend_id(self):
        """Return the technical id for the backend"""
        wallet = self.comchain_wallet_parsed
        currency_name = (
            wallet.get("server", {}).get("name", {})
            or self.env.user.company_id.comchain_currency_name
        )
        if not currency_name:
            ## not present in wallet and not configured in general settings
            return False
        return "%s:%s" % ("comchain", currency_name)

    @property
    def comchain_backend_accounts_data(self):
        """Return normalized backend account's data"""
        backend_id = self.comchain_backend_id
        if not backend_id:
            ## Comchain financial backend is not configured in general settings
            return []
        comchain_product = self.env.ref("lcc_comchain_base.product_product_comchain").sudo()
        data = {
            "type": backend_id,
            "accounts": [],
            "min_credit_amount": getattr(comchain_product, "sale_min_qty", 0),
            "max_credit_amount": getattr(comchain_product, "sale_max_qty", 0),
        }
        wallet = self.comchain_wallet_parsed
        if wallet:
            data["accounts"].append(
                {
                    "wallet": wallet,
                    "message_key": self.comchain_message_key,
                    "active": self.status == "active",
                }
            )
        return [data]

    @api.depends("name", "type", "comchain_status")
    def _compute_status(self):
        super(ResPartnerBackend, self)._compute_status()
        for record in self:
            if record.type == "comchain":
                if record.comchain_status == "active":
                    record.status = "active"
                elif record.comchain_status == "blocked":
                    record.status = "blocked"
                elif record.comchain_status == "disabled":
                    record.status = "inactive"
                elif record.comchain_status == "pending":
                    record.status = "to_confirm"
                else:
                    record.status = ""

    @api.multi
    def activate(self, type, credit_min=0, credit_max=0):
        self.ensure_one()
        self.write(
            {
                "comchain_status": "active",
                "comchain_type": "%s" % type,
                "comchain_credit_min": credit_min,
                "comchain_credit_max": credit_max,
            }
        )

    def credit_wallet(self, amount=0):
        """Send credit request to the financial backend"""
        self.ensure_one()
        res = super(ResPartnerBackend, self).credit_wallet(amount)
        if self.type != "comchain":
            return res

        company = self.partner_id.company_id
        # Get Odoo wallet
        try:
            odoo_wallet = pyc3l.Wallet.from_json(
                company.odoo_wallet_partner_id.lcc_backend_ids[0].comchain_wallet
            )
        except Exception as e:
            _logger.error(http.format_last_exception())
            return {
                "success": False,
                "response": "",
                "error": "Couldn't load wallet from database: %s" % e,
            }

        # Unlock Odoo wallet before sending a transaction
        try:
            odoo_wallet.unlock(company.comchain_odoo_wallet_password)
        except Exception as e:
            _logger.error(http.format_last_exception())
            return {
                "success": False,
                "response": "",
                "error": "Failed to unlock wallet: %s" % e,
            }

        # Send a transaction
        response = ""
        try:
            response = odoo_wallet.transferOnBehalfOf(
                "0x%s" % company.safe_wallet_partner_id.lcc_backend_ids[0].comchain_id,
                "0x%s" % self.comchain_id,
                amount,
                message_from=company.message_from,
                message_to=company.message_to,
            )
        except Exception as e:
            _logger.error(http.format_last_exception())
            return {
                "success": False,
                "response": response,
                "error": "Failed transfer on behalf transaction: %s" % e,
            }

        # Verify the Comchain transaction - res supposed to be the transaction hash
        if not re.search("^0x[0-9a-f]{64,64}$", response, re.IGNORECASE):
            return {
                "success": False,
                "response": response,
                "error": "Comchain transaction failed: TransferOnBehalofOf response is not the expected hash",
            }

        transaction = pyc3l.Transaction(response)
        if transaction.data["recieved"] != round(amount * 100):
            return {
                "success": False,
                "response": response,
                "error": "Order sent, but checking transaction record returned as an unexepected amount of '%s' received."
                % transaction.data["recieved"],
            }

        # All checks performed
        return {"success": True, "response": response, "error": ""}

    def get_lcc_product(self):
        product = super(ResPartnerBackend, self).get_lcc_product()
        if self.type == "comchain":
            product = self.env.ref("lcc_comchain_base.product_product_comchain")
        return product

    @api.model
    def translate_backend_key_in_wallet_name(self, backend_key):
        name = super(ResPartnerBackend, self).translate_backend_key_in_wallet_name(
            backend_key
        )
        if backend_key == "comchain:" + self.env.user.company_id.comchain_currency_name:
            name = "comchain"
        elif backend_key.startswith("comchain:"):
            name = backend_key
        return name

    def get_wallet_data(self):
        self.ensure_one()
        data = super(ResPartnerBackend, self).get_wallet_data()
        if self.type == "comchain":
            data = [
                "comchain:%s" % self.env.user.company_id.comchain_currency_name,
                self.comchain_id,
            ]
        return data
