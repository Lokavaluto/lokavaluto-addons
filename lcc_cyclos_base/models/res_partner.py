import json
import logging

import requests
from odoo import models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Inherits partner, adds Cyclos fields in the partner form, and functions."""

    _inherit = "res.partner"

    def cyclos_add_user(self, alt_currency_id) -> None:
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
                    },
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
                    },
                ],
            }
            try:
                res = alt_currency_id.cyclos_rest_call(
                    "POST",
                    "/users",
                    data=data,
                )
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 422:
                    msg = alt_currency_id.build_cyclos_error_message(e)
                    if msg != "":
                        msg = "Cyclos serveur complained about:\n{}".format(
                            "\n".join(msg)
                        )
                        raise ValueError(
                            msg,
                            e.response,
                        )
                raise

            data = json.loads(res.text)
            if data:
                _logger.debug(f"data: {data}")
                backend_obj.create(
                    {
                        "partner_id": record.id,
                        "alt_currency_id": alt_currency_id.id,
                        "cyclos_id": data.get("user")["id"]
                        if data.get("user", False)
                        else "",
                        "cyclos_status": data.get("status", ""),
                        "name": "cyclos:{}".format(data.get("user")["id"]),
                        "type": "cyclos",
                        "cyclos_create_response": res.text,
                    },
                )

    def show_app_access_buttons(self):
        # For Cyclos, we display the app access buttons on portal
        # only if the user has at least one activated Cyclos wallet
        res = super().show_app_access_buttons()
        for backend in self.lcc_backend_ids:
            if (backend.type == "cyclos") and (backend.status == "active"):
                res = True
                break
        return res
