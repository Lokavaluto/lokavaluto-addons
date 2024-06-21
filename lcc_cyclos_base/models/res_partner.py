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
                res = self.env.user.company_id.cyclos_rest_call("POST", "/users", data=data)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 422:
                    msg = self.env.user.company_id.build_cyclos_error_message(e)
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
