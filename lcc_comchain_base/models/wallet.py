import json
import logging
import re
import time

from pyc3l import Pyc3l
from pyc3l.ApiHandling import APIError

from odoo import api, fields, models

from odoo.addons.lcc_lokavaluto_app_connection import tools

pyc3l = Pyc3l()
_logger = logging.getLogger(__name__)


class ResPartnerBackend(models.Model):
    """Add backend commom property for local currency"""

    _inherit = "res.partner.backend"

    comchain_id = fields.Char(string="Address", tracking=True)
    comchain_wallet = fields.Text(string="Crypted json wallet", tracking=True)
    comchain_status = fields.Char(string="Comchain Status", tracking=True)
    comchain_type = fields.Selection(
        [("0", "Personal"), ("1", "Company"), ("2", "Admin")],
        string="Type",
        tracking=True,
    )
    comchain_credit_min = fields.Float(string="Min Credit limit", tracking=True)
    comchain_credit_max = fields.Float(string="Max Credit limit", tracking=True)
    comchain_message_key = fields.Char(string="Message keys", tracking=True)

    @property
    def comchain_wallet_parsed(self):
        return json.loads(self.comchain_wallet) if self.comchain_wallet else {}

    def write(self, vals):
        if vals.get("comchain_id"):
            vals["ident"] = vals.get("comchain_id")
        return super(ResPartnerBackend, self).write(vals)

    def get_wallet_json_data(self):
        """Returns normalized wallet data in JSON

        By default, and if no wallet in self, only return alt_currency json data.
        Need to be overrided by financial backend add-ons.

        """
        data = super().get_wallet_json_data()

        if self.comchain_wallet_parsed:
            data["accounts"].append(
                {
                    "wallet": self.comchain_wallet_parsed,
                    "message_key": self.comchain_message_key,
                    "active": self.status == "active",
                    "is_topup_allowed": self.is_topup_allowed,
                }
            )

        safe_wallet_partner = self.alt_currency_id.safe_wallet_partner_id

        if safe_wallet_partner and self.is_reconversion_allowed:
            safe_wallet_profile_info = safe_wallet_partner.lcc_profile_info()
            if safe_wallet_profile_info:
                if len(safe_wallet_profile_info) > 1:
                    raise ValueError("Safe partner has more than one public profile")

                ## Safe wallet is configured and has a public profile
                data["safe_wallet_recipient"] = safe_wallet_profile_info[0]

                monujo_backends = (
                    safe_wallet_partner.lcc_backend_ids._update_search_data(
                        [self.alt_currency_id.uri]
                    )
                )
                if len(monujo_backends) > 1:
                    raise ValueError("Safe partner has more than one wallet")
                data["safe_wallet_recipient"]["monujo_backends"] = monujo_backends

            else:
                _logger.error(
                    "Safe wallet %s has no public profile",
                    safe_wallet_partner.name,
                )

        return data

    @api.depends("name", "type", "comchain_status")
    def _compute_status(self):
        super()._compute_status()
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
        res = super().credit_wallet(amount)
        if self.type != "comchain":
            return res

        # Get Odoo wallet
        try:
            odoo_wallet = pyc3l.Wallet.from_json(
                self.alt_currency_id.odoo_wallet_partner_id.lcc_backend_ids[
                    0
                ].comchain_wallet,
            )
        except Exception as e:
            _logger.error(tools.format_last_exception())
            return {
                "success": False,
                "response": "",
                "error": "Couldn't load wallet from database: %s" % e,
            }

        # Unlock Odoo wallet before sending a transaction
        alt_currency = self.alt_currency_id
        try:
            odoo_wallet.unlock(alt_currency.comchain_odoo_wallet_password)
        except Exception as e:
            _logger.error(tools.format_last_exception())
            return {
                "success": False,
                "response": "",
                "error": "Failed to unlock wallet: %s" % e,
            }

        # Send a transaction
        response = ""
        try:
            response = odoo_wallet.transferOnBehalfOf(
                f"0x{alt_currency.safe_wallet_partner_id.lcc_backend_ids[0].comchain_id}",
                f"0x{self.comchain_id}",
                amount,
                message_from=self.alt_currency_id.message_from,
                message_to=self.alt_currency_id.message_to,
            )
        except Exception as e:
            _logger.error(tools.format_last_exception())
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

        retry = 0
        while True:
            tx_data = None
            try:
                tx_data = transaction.data
            except APIError as e:
                if not e.args[0].startswith("API Call failed without message"):
                    _logger.error(tools.format_last_exception())
                    return {
                        "success": False,
                        "response": response,
                        "error": "Failure when trying to get transaction info: %s" % e,
                    }
            if tx_data is not None:
                received = tx_data.get("recieved")
                if received is None:
                    _logger.error(
                        "Received incomplete transaction data. Missing 'recieved' field."
                    )
                else:
                    break
            retry += 1
            if retry >= 10:
                return {
                    "success": False,
                    "response": response,
                    "error": "Max retry reached to get transaction info (10 retries)",
                }
            time.sleep(0.5)
        if received != round(amount * 100):
            return {
                "success": False,
                "response": response,
                "error": "Order sent, but checking transaction record returned as an unexepected amount of '%s' received."
                % received,
            }

        # All checks performed
        return {"success": True, "response": response, "error": ""}

    def get_wallet_data(self):
        self.ensure_one()
        data = super().get_wallet_data()
        if self.type == "comchain":
            data = [
                f"comchain:{self.alt_currency_id.ident}",
                self.comchain_id,
            ]
        return data

    def get_wallet_balance(self):
        self.ensure_one()
        res = super().get_wallet_balance()
        if self.type != "comchain":
            return res

        wallet = pyc3l.Wallet.from_json(self.comchain_wallet)
        try:
            balance = wallet.nantBalance
        except Exception as e:
            _logger.error(tools.format_last_exception())
            return {
                "success": False,
                "response": "",
                "error_message": "Failed to get wallet balance: %s" % e,
            }

        return {"success": True, "response": balance}
