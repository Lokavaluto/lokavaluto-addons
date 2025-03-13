import json
import logging

from odoo import api, fields, models
from odoo.addons.lcc_lokavaluto_app_connection import tools

_logger = logging.getLogger(__name__)


class ResPartnerBackend(models.Model):
    """Add backend commom property for local currency."""

    _inherit = "res.partner.backend"

    cyclos_create_response = fields.Text(string="Cyclos create response")
    cyclos_id = fields.Char(string="Cyclos id")
    cyclos_status = fields.Char(string="Cyclos Status")

    def _update_search_data(self, backend_keys):
        data = super()._update_search_data(backend_keys)
        for wallet in self:
            if wallet.type != "cyclos":
                continue
            for backend_key in backend_keys:
                if backend_key.startswith("cyclos:") and wallet.cyclos_id:
                    data[backend_key] = [wallet.cyclos_id]
        return data

    @property
    def cyclos_backend_json_data(self):
        """Return normalized backend account's data."""
        backend_key = "{}:{}".format(
            "cyclos",
            self.alt_currency_id.get_cyclos_server_domain(),
        )
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
                    "url": self.alt_currency_id.cyclos_server_url,
                    "active": self.status == "active",
                    "is_topup_allowed": self.is_topup_allowed,
                },
            )

        safe_wallet_partner = self.alt_currency_id.cyclos_debit_wallet_partner

        if safe_wallet_partner and self.is_reconversion_allowed:
            safe_wallet_profile_info = safe_wallet_partner.lcc_profile_info()
            if safe_wallet_profile_info:
                if len(safe_wallet_profile_info) > 1:
                    msg = "Safe partner has more than one public profile"
                    raise ValueError(msg)

                ## Safe wallet is configured and has a public profile
                data["safe_wallet_recipient"] = safe_wallet_profile_info[0]

                monujo_backends = (
                    safe_wallet_partner.lcc_backend_ids._update_search_data(
                        [backend_key],
                    )
                )
                if len(monujo_backends) > 1:
                    msg = "Safe partner has more than one wallet"
                    raise ValueError(msg)
                data["safe_wallet_recipient"]["monujo_backends"] = monujo_backends

            else:
                _logger.error(
                    "Safe wallet %s has no public profile",
                    safe_wallet_partner.name,
                )
        return [data]

    @api.depends("name", "type", "cyclos_status")
    def _compute_status(self) -> None:
        super()._compute_status()
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

    def cyclos_validate_user(self) -> None:
        for record in self:
            if record.cyclos_status == "pending":
                res = record.alt_currency_id.cyclos_rest_call(
                    "POST",
                    f"/{record.cyclos_id}/registration/validate",
                )
                _logger.debug(f"res: {res.text}")
                data = json.loads(res.text)
                if data.get("status", False) and data.get("status") == "active":
                    record.write(
                        {
                            "cyclos_status": data.get("status", ""),
                            "cyclos_create_response": res.text,
                        },
                    )

    def cyclos_activate_user(self) -> None:
        for record in self:
            if record.cyclos_status != "active":
                data = {"status": "active", "comment": "Activated by Odoo"}
                record.alt_currency_id.cyclos_rest_call(
                    "POST",
                    f"/{record.cyclos_id}/status",
                    data=data,
                )
                res = record.alt_currency_id.cyclos_rest_call(
                    "GET",
                    f"/{record.cyclos_id}/status",
                )
                _logger.debug(f"res: {res}")
                data_res = json.loads(res.text)
                record.write(
                    {
                        "cyclos_status": data_res.get("status", ""),
                    },
                )

    def cyclos_block_user(self) -> None:
        for record in self:
            if record.cyclos_status != "blocked":
                data = {"status": "blocked", "comment": "Blocked by Odoo"}
                record.alt_currency_id.cyclos_rest_call(
                    "POST",
                    f"/{record.cyclos_id}/status",
                    data=data,
                )
                res = record.alt_currency_id.cyclos_rest_call(
                    "GET",
                    f"/{record.cyclos_id}/status",
                )
                _logger.debug(f"res: {res}")
                data_res = json.loads(res.text)
                record.write(
                    {
                        "cyclos_status": data_res.get("status", ""),
                    },
                )

    def cyclos_disable_user(self) -> None:
        for record in self:
            if record.cyclos_status != "disabled":
                data = {"status": "disabled", "comment": "Disabled by Odoo"}
                record.alt_currency_id.cyclos_rest_call(
                    "POST",
                    f"/{record.cyclos_id}/status",
                    data=data,
                )
                res = record.alt_currency_id.cyclos_rest_call(
                    "GET",
                    f"/{record.cyclos_id}/status",
                )
                _logger.debug(f"res: {res}")
                data_res = json.loads(res.text)
                record.write(
                    {
                        "cyclos_status": data_res.get("status", ""),
                    },
                )

    def force_cyclos_password(self, password) -> None:
        for record in self:
            # TODO: need to stock password type id from cyclos API and replace -4307382460900696903
            data = {
                "newPassword": password,
                "checkConfirmation": True,
                "newPasswordConfirmation": password,
                "forceChange": False,
            }
            try:
                record.alt_currency_id.cyclos_rest_call(
                    "POST",
                    "/{}/passwords/{}/change".format(
                        record.cyclos_id,
                        "-4307382460900696903",
                    ),
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
        for record in self:
            res = record.alt_currency_id.cyclos_rest_call(
                "POST",
                "/auth/session",
                data={"timeoutInSeconds": 90000},
                api_login=api_login,
                api_password=api_password,
            )
            _logger.debug(f"res TOKEN: {res.text}")
            data = json.loads(res.text)
            return data.get("sessionToken", False)
        return None

    def cyclos_remove_user_token(self, api_login, api_password) -> None:
        for record in self:
            res = record.alt_currency_id.cyclos_rest_call(
                "DELETE",
                "/auth/session",
                api_login=api_login,
                api_password=api_password,
            )
            _logger.debug(f"res: {res.text}")

    def credit_wallet(self, amount=0):
        """Send credit request to the financial backend."""
        self.ensure_one()
        res = super().credit_wallet(amount)
        if self.type != "cyclos":
            return res

        data = {
            "amount": amount,
            "description": f"Credited by {self.alt_currency_id.name}",
            "subject": self.cyclos_id,
            "type": "debit.toPro" if self.partner_id.is_company else "debit.toUser",
        }
        _logger.debug(f"data: {data}")
        response = self.alt_currency_id.cyclos_rest_call(
            "POST",
            "/system/payments",
            data=data,
        )
        _logger.debug(f"response: {response}")
        # TODO: need to check response
        return {"success": True, "response": response}

    def get_wallet_data(self):
        self.ensure_one()
        data = super().get_wallet_data()
        if self.type == "cyclos":
            data = [
                "cyclos:cyclos",
                self.cyclos_id,
            ]
        return data

    def get_wallet_balance(self):
        self.ensure_one()
        res = super().get_wallet_balance()
        if self.type != "cyclos":
            return res
        try:
            res = self._cyclos_rest_call("GET", f"/{self.cyclos_id}/accounts")
            _logger.debug(f"res: {res}")
        except Exception as e:
            _logger.exception(tools.format_last_exception())
            return {
                "success": False,
                "response": "",
                "error_message": f"Failed to get wallet balance: {e}",
            }

        data_res = json.loads(res.text)
        balance = float(data_res[0].get("status", {}).get("balance", ""))

        return {"success": True, "response": balance}
