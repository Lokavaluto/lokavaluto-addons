import requests
import json
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResPartnerBackend(models.Model):
    """Add backend commom property for local currency"""

    _inherit = "res.partner.backend"

    type = fields.Selection(selection_add=[("cyclos", "Cyclos")])
    cyclos_create_response = fields.Text(string="Cyclos create response")
    cyclos_id = fields.Char(string="Cyclos id")
    cyclos_status = fields.Char(string="Cyclos Status")

    @api.depends("name", "type", "cyclos_status")
    def _compute_status(self):
        super(ResPartnerBackend, self)._compute_status()
        if self.type == "cyclos":
            if self.cyclos_status == "active":
                self.status = "active"
            elif self.cyclos_status == "blocked":
                self.status = "blocked"
            elif self.cyclos_status == "disabled":
                self.status = "inactive"
            elif self.cyclos_status == "pending":
                self.status = "to_confirm"
            else:
                self.status = ""

    def _build_cyclos_error_message(self, e):
        json_error = e.response.json()
        msg = ""
        if json_error.get("code") == "validation":
            if json_error.get("propertyErrors"):
                error = json_error.get("propertyErrors")
            elif json_error.get("generalErrors"):
                error = json_error.get("generalErrors")
            msg = ["  - %s: %s" % (k, ", ".join(v)) for k, v in error.items()]
        return msg

    def _cyclos_rest_call(
        self, method, entrypoint, data={}, api_login=False, api_password=False
    ):
        headers = {"Content-type": "application/json", "Accept": "text/plain"}
        requests.packages.urllib3.disable_warnings()
        if not api_login:
            api_login = self.env.user.company_id.cyclos_server_login
        if not api_password:
            api_password = self.env.user.company_id.cyclos_server_password
        api_url = "%s%s" % (self.env.user.company_id.cyclos_server_url, entrypoint)
        res = requests.request(
            method.lower(),
            api_url,
            auth=HTTPBasicAuth(api_login, api_password),
            verify=False,
            data=json.dumps(data),
            headers=headers,
        )
        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception("404 when trying to reach cyclos on %s" % api_url)
            try:
                json_output = e.response.json()
                _logger.debug(e.response.json())
            except ValueError as e:
                raise Exception("Non-json output from cyclos on %s" % api_url)
                _logger.debug(e.response.text)

            if e.response.status_code == 422:
                msg = self._build_cyclos_error_message(e)
                if msg != "":
                    raise ValueError(
                        "Cyclos serveur complained about:\n%s" % "\n".join(msg),
                        e.response,
                    )
            raise
        return res

    @api.multi
    def cyclos_validate_user(self):
        for record in self:
            if record.cyclos_status == "pending":
                res = record._cyclos_rest_call(
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

    @api.multi
    def cyclos_activate_user(self):
        for record in self:
            if record.cyclos_status != "active":
                data = {"status": "active", "comment": "Activated by Odoo"}
                record._cyclos_rest_call(
                    "POST", "/%s/status" % record.cyclos_id, data=data
                )
                res = record._cyclos_rest_call("GET", "/%s/status" % record.cyclos_id)
                _logger.debug("res: %s" % res)
                data_res = json.loads(res.text)
                record.write(
                    {
                        "cyclos_status": data_res.get("status", ""),
                    }
                )

    @api.multi
    def cyclos_block_user(self):
        for record in self:
            if record.cyclos_status != "blocked":
                data = {"status": "blocked", "comment": "Blocked by Odoo"}
                record._cyclos_rest_call(
                    "POST", "/%s/status" % record.cyclos_id, data=data
                )
                res = record._cyclos_rest_call("GET", "/%s/status" % record.cyclos_id)
                _logger.debug("res: %s" % res)
                data_res = json.loads(res.text)
                record.write(
                    {
                        "cyclos_status": data_res.get("status", ""),
                    }
                )

    @api.multi
    def cyclos_disable_user(self):
        for record in self:
            if record.cyclos_status != "disabled":
                data = {"status": "disabled", "comment": "Disabled by Odoo"}
                record._cyclos_rest_call(
                    "POST", "/%s/status" % record.cyclos_id, data=data
                )
                res = record._cyclos_rest_call("GET", "/%s/status" % record.cyclos_id)
                _logger.debug("res: %s" % res)
                data_res = json.loads(res.text)
                record.write(
                    {
                        "cyclos_status": data_res.get("status", ""),
                    }
                )

    def force_cyclos_password(self, password):
        for record in self:
            # TODO: need to stock password type id from cyclos API and replace -4307382460900696903
            data = {
                "newPassword": password,
                "checkConfirmation": True,
                "newPasswordConfirmation": password,
                "forceChange": False,
            }
            try:
                record._cyclos_rest_call(
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
        for record in self:
            res = record._cyclos_rest_call(
                "POST",
                "/auth/session",
                data={"timeoutInSeconds": 90000},
                api_login=api_login,
                api_password=api_password,
            )
            _logger.debug("res TOKEN: %s" % res.text)
            data = json.loads(res.text)
            return data.get("sessionToken", False)

    @api.multi
    def cyclos_remove_user_token(self, api_login, api_password):
        for record in self:
            res = record._cyclos_rest_call(
                "DELETE",
                "/auth/session",
                api_login=api_login,
                api_password=api_password,
            )
            _logger.debug("res: %s" % res.text)

    def credit_wallet(self, amount=0):
        """Send credit request to the financial backend"""
        self.ensure_one()
        res = super(ResPartnerBackend,self).credit_wallet(amount)
        if self.type == "cyclos":
            data = {
                "amount": amount,
                "description": "Credited by %s" % self.partner_id.company_id.name,
                "subject": self.cyclos_id,
                "type": "debit.toPro"
                if self.partner_id.is_company
                else "debit.toUser",
            }
            _logger.debug("data: %s" % data)
            response = self._cyclos_rest_call("POST", "/system/payments", data=data)
            _logger.debug("response: %s" % response)
            #TODO: need to check response
            res = {
                "success": True,
                "response": response
            }
        return res

    def get_lcc_product(self):
        product = super(ResPartnerBackend,self).get_lcc_product()
        if self.type == "cyclos":
            product = self.env.ref("lcc_cyclos_base.product_product_cyclos")
        return product

    def get_wallet_data(self):
        self.ensure_one()
        data = super(ResPartnerBackend,self).get_wallet_data()
        if self.type == "cyclos":
            data = [ 
                "cyclos:cyclos",
                self.cyclos_id,
            ]
        return data
         