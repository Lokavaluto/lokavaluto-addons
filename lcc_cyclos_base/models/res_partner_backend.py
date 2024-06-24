import requests
import json
from odoo import models, fields, api
from odoo.addons.lcc_lokavaluto_app_connection import tools
import logging

_logger = logging.getLogger(__name__)


class ResPartnerBackend(models.Model):
    """Add backend commom property for local currency"""

    _inherit = "res.partner.backend"

    type = fields.Selection(selection_add=[("cyclos", "Cyclos")], ondelete={'cyclos': 'cascade'})
    cyclos_create_response = fields.Text(string="Cyclos create response")
    cyclos_id = fields.Char(string="Cyclos id")
    cyclos_status = fields.Char(string="Cyclos Status")

    def _update_search_data(self, backend_keys):
        data = super(ResPartnerBackend, self)._update_search_data(backend_keys)
        for wallet in self: 
            if wallet.type != "cyclos":
                continue
            for backend_key in backend_keys:
                if backend_key.startswith("cyclos:") and wallet.cyclos_id:
                    data[backend_key] = [wallet.cyclos_id]
        return data

    @property
    def cyclos_backend_json_data(self):
        """Return normalized backend account's data"""
        backend_key = "%s:%s" % ("cyclos", self.env.user.company_id.get_cyclos_server_domain())
        cyclos_product = self.env.ref("lcc_cyclos_base.product_product_cyclos").sudo()
        data = {
            "type": backend_key,
            "accounts": [],
            "min_credit_amount": getattr(cyclos_product, "sale_min_qty", 0),
            "max_credit_amount": getattr(cyclos_product, "sale_max_qty", 0),
        }
        if self.cyclos_id:
            data["accounts"].append(
                {
                    "owner_id": self.cyclos_id,
                    "url": self.env.user.company_id.cyclos_server_url,
                    "active": self.status == "active",
                }
            )

        company = self.partner_id.company_id
        safe_wallet_partner = company.cyclos_debit_wallet_partner

        if safe_wallet_partner:

            safe_wallet_profile_info = safe_wallet_partner.lcc_profile_info()
            if safe_wallet_profile_info:
                if len(safe_wallet_profile_info) > 1:
                    raise ValueError("Safe partner has more than one public profile")

                ## Safe wallet is configured and has a public profile
                data["safe_wallet_recipient"] = safe_wallet_profile_info[0]

                monujo_backends = safe_wallet_partner.lcc_backend_ids._update_search_data(
                    [backend_key]
                )
                if len(monujo_backends) > 1:
                    raise ValueError("Safe partner has more than one wallet")
                data["safe_wallet_recipient"]["monujo_backends"] = monujo_backends

            else:
                _logger.error(
                    "Safe wallet %s has no public profile",
                    safe_wallet_partner.name,
                )
        return [data]

    @api.depends("name", "type", "cyclos_status")
    def _compute_status(self):
        super(ResPartnerBackend, self)._compute_status()
        for rec in self: 
            if rec.type == "cyclos":
                if rec.cyclos_status == "active":
                    rec.status = "active"
                elif rec.cyclos_status == "blocked":
                    rec.status = "blocked"
                elif rec.cyclos_status == "disabled":
                    rec.status = "inactive"
                elif rec.cyclos_status == "pending":
                    rec.status = "to_confirm"
                else:
                    rec.status = ""

    def cyclos_validate_user(self):
        company_id = self.env.user.company_id
        for record in self:
            if record.cyclos_status == "pending":
                res = company_id.cyclos_rest_call(
                    "POST", "/%s/registration/validate" % record.cyclos_id
                )
                _logger.debug("res: %s" % res.text)
                data = json.loads(res.text)
                if data.get("status", False) and data.get("status") == "active":
                    record.write(
                        {
                            "cyclos_status": data.get("status", ""),
                            "cyclos_create_response": res.text,
                        }
                    )

    def cyclos_activate_user(self):
        company_id = self.env.user.company_id
        for record in self:
            if record.cyclos_status != "active":
                data = {"status": "active", "comment": "Activated by Odoo"}
                company_id.cyclos_rest_call(
                    "POST", "/%s/status" % record.cyclos_id, data=data
                )
                res = company_id.cyclos_rest_call("GET", "/%s/status" % record.cyclos_id)
                _logger.debug("res: %s" % res)
                data_res = json.loads(res.text)
                record.write(
                    {
                        "cyclos_status": data_res.get("status", ""),
                    }
                )

    def cyclos_block_user(self):
        company_id = self.env.user.company_id
        for record in self:
            if record.cyclos_status != "blocked":
                data = {"status": "blocked", "comment": "Blocked by Odoo"}
                company_id.cyclos_rest_call(
                    "POST", "/%s/status" % record.cyclos_id, data=data
                )
                res = company_id.cyclos_rest_call("GET", "/%s/status" % record.cyclos_id)
                _logger.debug("res: %s" % res)
                data_res = json.loads(res.text)
                record.write(
                    {
                        "cyclos_status": data_res.get("status", ""),
                    }
                )

    def cyclos_disable_user(self):
        company_id = self.env.user.company_id
        for record in self:
            if record.cyclos_status != "disabled":
                data = {"status": "disabled", "comment": "Disabled by Odoo"}
                company_id.cyclos_rest_call(
                    "POST", "/%s/status" % record.cyclos_id, data=data
                )
                res = company_id.cyclos_rest_call("GET", "/%s/status" % record.cyclos_id)
                _logger.debug("res: %s" % res)
                data_res = json.loads(res.text)
                record.write(
                    {
                        "cyclos_status": data_res.get("status", ""),
                    }
                )

    def force_cyclos_password(self, password):
        company_id = self.env.user.company_id
        for record in self:
            # TODO: need to stock password type id from cyclos API and replace -4307382460900696903
            data = {
                "newPassword": password,
                "checkConfirmation": True,
                "newPasswordConfirmation": password,
                "forceChange": False,
            }
            try:
                company_id.cyclos_rest_call(
                    "POST",
                    "/%s/passwords/%s/change"
                    % (record.cyclos_id, "-4307382460900696903"),
                    data=data,
                )
            except ValueError as e:
                if (
                    len(e.args) > 1
                    and e.args[1].status_code == 422
                    and "newPassword" in e.args[1].json().get("properties", [])
                ):
                    _logger.debug("Ignoring Cyclos NewPassword Error !")
                else:
                    raise

    def cyclos_create_user_token(self, api_login, api_password):
        self.ensure_one()
        company_id = self.env.user.company_id
        for record in self:
            res = company_id.cyclos_rest_call(
                "POST",
                "/auth/session",
                data={"timeoutInSeconds": 90000},
                api_login=api_login,
                api_password=api_password,
            )
            _logger.debug("res TOKEN: %s" % res.text)
            data = json.loads(res.text)
            return data.get("sessionToken", False)

    def cyclos_remove_user_token(self, api_login, api_password):
        company_id = self.env.user.company_id
        for record in self:
            res = company_id.cyclos_rest_call(
                "DELETE",
                "/auth/session",
                api_login=api_login,
                api_password=api_password,
            )
            _logger.debug("res: %s" % res.text)

    def credit_wallet(self, amount=0):
        """Send credit request to the financial backend"""
        self.ensure_one()
        res = super(ResPartnerBackend, self).credit_wallet(amount)
        if self.type != "cyclos":
            return res

        data = {
            "amount": amount,
            "description": "Credited by %s" % self.partner_id.company_id.name,
            "subject": self.cyclos_id,
            "type": "debit.toPro" if self.partner_id.is_company else "debit.toUser",
        }
        _logger.debug("data: %s" % data)
        response = self.env.user.company_id.cyclos_rest_call("POST", "/system/payments", data=data)
        _logger.debug("response: %s" % response)
        # TODO: need to check response
        res = {"success": True, "response": response}
        return res

    def get_lcc_product(self):
        product = super(ResPartnerBackend, self).get_lcc_product()
        if self.type == "cyclos":
            product = self.env.ref("lcc_cyclos_base.product_product_cyclos")
        return product

    @api.model
    def translate_backend_key_in_wallet_name(self, backend_key):
        name = super(ResPartnerBackend, self).translate_backend_key_in_wallet_name(
            backend_key
        )
        if backend_key == "cyclos":
            name = "cyclos"
        elif backend_key.startswith("cyclos:"):
            name = backend_key.replace(
                "@" + self.env.user.company_id.get_cyclos_server_domain(), ""
            )
        return name

    def get_wallet_data(self):
        self.ensure_one()
        data = super(ResPartnerBackend, self).get_wallet_data()
        if self.type == "cyclos":
            data = [
                "cyclos:cyclos",
                self.cyclos_id,
            ]
        return data

    def get_wallet_balance(self):
        self.ensure_one()
        res = ""
        try :
            res = self._cyclos_rest_call("GET", "/%s/accounts" % self.cyclos_id)
            _logger.debug("res: %s" % res)
        except Exception as e:
            _logger.error(tools.format_last_exception())
            return {
                "success": False,
                "response": "",
                "error_message": "Failed to get wallet balance: %s" % e,
            }
        
        data_res = json.loads(res.text)
        balance = float(data_res[0].get("status", {}).get("balance", ""))

        return {
            "success": True,
            "response": balance
        }