import json
import logging

from ..utils import check_transaction_content

from pyc3l import Pyc3l
from pyc3l.ApiHandling import APIError

from odoo import api, fields, models

from odoo.addons.lcc_lokavaluto_app_connection import tools
from odoo.exceptions import MissingError


pyc3l = Pyc3l()
_logger = logging.getLogger(__name__)


class ResPartnerBackend(models.Model):
    """Add backend commom property for local currency"""

    _inherit = "res.partner.backend"

    comchain_id = fields.Char(string="Address", tracking=True)
    comchain_wallet = fields.Text(string="Crypted json wallet", tracking=True)
    comchain_status = fields.Char(string="Comchain Status", tracking=True)
    comchain_type = fields.Selection(
        [
            ("0", "Personal"),
            ("1", "Professional"),
            ("2", "Admin"),
            ("3", "Pledge Admin"),
            ("4", "Property Admin"),
        ],
        string="Type",
        tracking=True,
    )
    comchain_credit_min = fields.Float(string="Min Credit limit", tracking=True)
    comchain_credit_max = fields.Float(string="Max Credit limit", tracking=True)
    comchain_message_key = fields.Char(string="Message keys", tracking=True)
    comchain_wallet_pwd = fields.Char(string="Wallet Password")

    @property
    def comchain_wallet_parsed(self):
        return json.loads(self.comchain_wallet) if self.comchain_wallet else {}

    # Permissions are tuples (not sets) because they transit through
    # Odoo's env.context which may be serialized in RPC/caching paths.
    _ALL_COMCHAIN_PERMS = ("set_admin", "set_property", "pledge")

    _TYPE_PERMS = {
        "0": (),  # personal
        "1": (),  # professional
        "2": ("set_admin", "set_property", "pledge"),  # admin
        "3": ("pledge",),  # pledgeAdmin
        "4": ("set_property",),  # propertyAdmin
    }

    def get_auth_context(self):
        """Return comchain-specific auth enrichment data for this wallet.

        If the wallet's owner (``self.partner_id.user_ids``)
        belongs to the legacy ``group_wallet_full_manager`` group,
        full permissions are granted immediately (skip comchain
        data inspection).

        Otherwise, permissions are derived from ``comchain_type``
        via ``_TYPE_PERMS``.

        Returns:
            dict: ``{"comchain_perms": tuple}`` merged with base.
        """
        self.ensure_one()
        base_auth = super().get_auth_context()
        if self.type != "comchain":
            return base_auth
        if any(
            u.has_group("lcc_lokavaluto_app_connection.group_wallet_full_manager")
            for u in self.partner_id.user_ids
        ):
            perms = self._ALL_COMCHAIN_PERMS
        else:
            perms = self._TYPE_PERMS.get(self.comchain_type or "0", ())
        return {**base_auth, "comchain_perms": perms}

    # Maps comchain permissions to coarse-grained actions.
    _PERM_ACTIONS = {
        "set_admin": (
            "activate",
            "search-all-recipients",
            "validate-credit-request",
        ),
        "set_property": (
            "activate",
            "search-all-recipients",
        ),
        "pledge": ("validate-credit-request",),
    }

    def get_authorized_actions(self):
        """Map comchain permissions to coarse-grained actions.

        A disabled (non-active status) wallet has no actions.

        Returns:
            list: sorted, deduplicated action strings.
        """
        self.ensure_one()
        base_actions = super().get_authorized_actions()
        if self.type != "comchain":
            return base_actions
        if self.comchain_status != "active":
            return base_actions
        auth_data = self.get_auth_context()
        perms = auth_data.get("comchain_perms", ())
        actions = set(base_actions)
        for perm in perms:
            actions.update(self._PERM_ACTIONS.get(perm, ()))
        return sorted(actions)

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
                    "status": self.status,
                    "is_topup_allowed": self.is_topup_allowed,
                    "is_payment_request_allowed": self.is_payment_request_allowed,
                    "comchain": {
                        "accountType": int(self.comchain_type or "0"),
                        "status": self.comchain_status,
                        "lowLimit": self.comchain_credit_min,
                        "highLimit": self.comchain_credit_max,
                    },
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
        odoo_wallet = self.alt_currency_id.odoo_wallet_partner_id.lcc_backend_ids[0]
        try:
            comchain_odoo_wallet = pyc3l.Wallet.from_json(odoo_wallet.comchain_wallet)
        except Exception as e:
            _logger.error(tools.format_last_exception())
            return {
                "success": False,
                "response": "",
                "error": "Couldn't load wallet from database: %s" % e,
            }

        # Unlock Odoo wallet before sending a transaction
        try:
            comchain_odoo_wallet.unlock(odoo_wallet.comchain_wallet_pwd)
        except Exception as e:
            _logger.error(tools.format_last_exception())
            return {
                "success": False,
                "response": "",
                "error": "Failed to unlock wallet: %s" % e,
            }

        # Send a transaction
        alt_currency = self.alt_currency_id
        response = ""
        try:
            response = comchain_odoo_wallet.transferOnBehalfOf(
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

        message = check_transaction_content(response, amount)
        if message:
            return {
                "success": False,
                "response": response,
                "error": message,
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

    def send_nant_transaction(self, dest_wallet, amount, message_from="", message_to=""):
        self.ensure_one()
        if self.type != "comchain":
            return res

        if not self.comchain_wallet_pwd:
            raise MissingError("Transaction impossible - Wallet password missing")

        # Get Comchain wallet
        comchain_wallet = pyc3l.Wallet.from_json(self.comchain_wallet)

        # Unlock wallet before sending a transaction
        comchain_wallet.unlock(self.comchain_wallet_pwd)

        # Send a transaction
        response = comchain_wallet.transferNant(
            f"0x{dest_wallet.comchain_id}",
            amount,
            message_from=message_from,
            message_to=message_to,
        )

        message = check_transaction_content(response, amount)
        if message:
            raise APIError(message)

        # All checks performed
        return response
