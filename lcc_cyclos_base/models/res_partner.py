import requests
import json
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Inherits partner, adds Cyclos fields in the partner form, and functions"""

    _inherit = "res.partner"

    def _update_auth_data(self, password):
        self.ensure_one()
        data = super(ResPartner, self)._update_auth_data(password)
        # Update cyclos password with odoo one from authenticate session
        wallets = self.get_wallets("cyclos")
        if len(wallets) == 0:
            data.extend(self.env["res.partner.backend"].cyclos_backend_json_data)
        for wallet in wallets:
            wallet_json_data = wallet.cyclos_backend_json_data
            if wallet and wallet_json_data:
                wallet.force_cyclos_password(password)
                new_token = wallet.cyclos_create_user_token(self.id, password)
                if new_token:
                    for ua in wallet_json_data[0]["accounts"]:
                        ua["token"] = new_token
            data.extend(wallet_json_data)
        return data

    def _get_backend_credentials(self):
        self.ensure_one()
        data = super(ResPartner, self)._get_backend_credentials()
        wallets = self.get_wallets("cyclos")
        if len(wallets) == 0:
            data.extend(self.env["res.partner.backend"].cyclos_backend_json_data)
        for wallet in wallets:
            data.extend(wallet.cyclos_backend_json_data)
        return data

    def _update_search_data(self, backend_keys):
        self.ensure_one()
        data = super(ResPartner, self)._update_search_data(backend_keys)
        wallets = self.get_wallets("cyclos")
        for wallet in wallets:
            for backend_key in backend_keys:
                if backend_key.startswith("cyclos:") and wallet.cyclos_id:
                    data[backend_key] = [wallet.cyclos_id]
        return data

    def backends(self):
        self.ensure_one()
        backends = super(ResPartner, self).backends()
        wallets = self.get_wallets("cyclos")
        for wallet in wallets:
            if wallet.cyclos_id:
                backends = backends | {
                    "%s:%s"
                    % ("cyclos", self.env.user.company_id.get_cyclos_server_domain())
                }
        return backends

    @api.multi
    def cyclos_add_user(self):
        for record in self:
            backend_obj = self.env["res.partner.backend"]
            group = (
                "particuliers" if record.company_type == "person" else "professionnels"
            )
            data = {
                "username": record.id,
                "name": record.name,
                "email": record.email,
                "group": group,
                "passwords": [
                    {
                        "type": "login",
                        "value": "Odoo1234",
                        "checkConfirmation": True,
                        "confirmationValue": "Odoo1234",
                        "forceChange": False,
                    }
                ],
                "skipActivationEmail": True,
                "addresses": [
                    {
                        "name": record.name,
                        "addressLine1": record.street,
                        "addressLine2": record.street2,
                        "zip": record.zip,
                        "city": record.city,
                        "location": {
                            "latitude": record.partner_latitude,
                            "longitude": record.partner_longitude,
                        },
                        "defaultAddress": True,
                        "hidden": True,
                        "contactInfo": {
                            "email": record.email,
                            "mobilePhone": record.mobile.strip()
                            if record.mobile
                            else "",
                        },
                    }
                ],
            }
            try:
                res = backend_obj._cyclos_rest_call("POST", "/users", data=data)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 422:
                    msg = backend_obj._build_cyclos_error_message(e)
                    if msg != "":
                        raise ValueError(
                            "Cyclos serveur complained about:\n%s" % "\n".join(msg),
                            e.response,
                        )
                raise

            data = json.loads(res.text)
            if data:
                _logger.debug("data: %s" % data)
                backend_obj.create(
                    {
                        "partner_id": record.id,
                        "cyclos_id": data.get("user")["id"]
                        if data.get("user", False)
                        else "",
                        "cyclos_status": data.get("status", ""),
                        "name": "cyclos:%s" % data.get("user")["id"],
                        "type": "cyclos",
                        "cyclos_create_response": res.text,
                    }
                )

    def show_app_access_buttons(self):
        # For Cyclos, we display the app access buttons on portal
        # only if the user has at least one activated Cyclos wallet
        res = super(ResPartner, self).show_app_access_buttons()
        for backend in self.lcc_backend_ids:
            if (backend.type == "cyclos") and (backend.status == "active"):
                res = True
                break
        return res
