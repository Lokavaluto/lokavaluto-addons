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

    @property
    def _cyclos_backend_id(self):
        url = self.env.user.company_id.cyclos_server_url
        if not url:
            return False
        parsed_uri = urlparse(url)
        if (
            not parsed_uri or not parsed_uri.netloc
        ):  ## is backend available and configured on odoo
            return False
        domain = parsed_uri.netloc
        return "cyclos:%s" % domain

    def _cyclos_backend(self):
        # We only support one backend per type for now
        backend_data = self.env["res.partner.backend"]
        for backend in self.lcc_backend_ids:
            if backend.type == "cyclos":
                return backend
        return backend_data

    def _cyclos_backend_json_data(self):
        """Prepare backend data to be sent by credentials requests"""
        backend_data = self._cyclos_backend()
        backend_id = self._cyclos_backend_id
        if not backend_id:  ## is backend available and configured on odoo
            return []
        data = {
            "type": backend_id,
            "accounts": [],
        }
        if backend_data.cyclos_id:
            data["accounts"].append(
                {
                    "owner_id": backend_data.cyclos_id,
                    "url": self.env.user.company_id.cyclos_server_url,
                    "active": backend_data.status == "active",
                }
            )
        return [data]

    def _update_auth_data(self, password):
        self.ensure_one()
        data = super(ResPartner, self)._update_auth_data(password)
        # Update cyclos password with odoo one from authenticate session
        backend = self._cyclos_backend()
        backend_json_data = self._cyclos_backend_json_data()
        if backend and backend_json_data:
            backend.forceCyclosPassword(password)
            new_token = backend.createCyclosUserToken(self.id, password)
            if new_token:
                for ua in backend_json_data[0]["accounts"]:
                    ua["token"] = new_token
        data.extend(backend_json_data)
        return data

    def _get_backend_credentials(self):
        self.ensure_one()
        data = super(ResPartner, self)._get_backend_credentials()
        data.extend(self._cyclos_backend_json_data())
        return data

    def _update_search_data(self, backend_keys):
        self.ensure_one()
        backend_data = self._cyclos_backend()
        data = super(ResPartner, self)._update_search_data(backend_keys)
        for backend_key in backend_keys:
            if backend_key.startswith("cyclos:") and backend_data.cyclos_id:
                data[backend_key] = [backend_data.cyclos_id]
        return data

    def backends(self):
        self.ensure_one()
        backends = super(ResPartner, self).backends()
        if self._cyclos_backend().cyclos_id:
            cyclos_serveur_url = self.env.user.company_id.cyclos_server_url
            remove = ["https://", "http://", "/api"]
            for value in remove:
                cyclos_serveur_url = cyclos_serveur_url.replace(value, "")
            return backends | {"%s:%s" % ("cyclos", cyclos_serveur_url)}
        else:
            return backends

    @api.multi
    def cyclosCreateOrder(self, owner_id, amount):
        order = self.env["sale.order"]
        line = self.env["sale.order.line"]
        cyclos_product = self.env.ref("lcc_cyclos_base.product_product_cyclos")
        _logger.debug("PARTNER IN SELF?: %s(%s)" % (self.name, self.id))
        for partner in self:
            # TODO: case with contact of a company ?
            order_vals = {
                "partner_id": partner.id,
            }
            order_vals = order.play_onchanges(order_vals, ["partner_id"])
            _logger.debug("CYCLOS ORDER: %s" % order_vals)
            order_id = order.create(order_vals)
            line_vals = {
                "order_id": order_id.id,
                "product_id": cyclos_product.id,
            }
            line_vals = line.play_onchanges(line_vals, ["product_id"])
            line_vals.update(
                {
                    "product_uom_qty": amount,
                    "price_unit": 1,
                    # TODO: Taxes ?
                }
            )
            _logger.debug("CYCLOS ORDER LINE: %s" % line_vals)
            line.create(line_vals)
            order_id.write(
                {"state": "sent", "require_signature": False, "require_payment": True}
            )
        return order_id

    @api.multi
    def action_credit_cyclos_account(self, amount):
        for record in self:
            backend_data = record._cyclos_backend()
            if backend_data.status != "active":
                backend_data = record.parent_id._cyclos_backend()
            backend_data.credit_cyclos_account(amount)

    @api.multi
    def addCyclosUser(self):
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
