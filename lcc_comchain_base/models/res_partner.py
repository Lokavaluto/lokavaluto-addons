import json
from odoo import models, fields, api
import logging

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
        groups="lcc_comchain_base.group_comchain_manager",
    )
    comchain_credit_min = fields.Float(
        string="Min Credit limit", groups="lcc_comchain_base.group_comchain_manager"
    )
    comchain_credit_max = fields.Float(
        string="Max Credit limit", groups="lcc_comchain_base.group_comchain_manager"
    )
    comchain_message_key = fields.Char(string="Message keys")

    @property
    def comchain_wallet_parsed(self):
        return (
            json.loads(self.comchain_wallet)
            if self.comchain_wallet
            else {}
        )

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
            ## not present in wallet and not configured in general settings
            return []
        comchain_product = self.env.ref("lcc_comchain_base.product_product_comchain")
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
        if self.type == "comchain":
            if self.comchain_status == "active":
                self.status = "active"
            elif self.comchain_status == "blocked":
                self.status = "blocked"
            elif self.comchain_status == "disabled":
                self.status = "inactive"
            elif self.comchain_status == "pending":
                self.status = "to_confirm"
            else:
                self.status = ""


class ResPartner(models.Model):
    """Inherits partner:
    - add comchain fields in the partner form
    - add functions"""

    _inherit = "res.partner"

    def _update_auth_data(self, password):
        self.ensure_one()
        data = super(ResPartner, self)._update_auth_data(password)
        backend_data = self._comchain_backend()
        data.extend(backend_data.comchain_backend_accounts_data)
        return data

    def _comchain_backend(self):
        # We only support one backend per type for now
        backend_data = self.env["res.partner.backend"]
        for backend in self.lcc_backend_ids:
            if backend.type == "comchain":
                return backend
        return backend_data

    def _update_search_data(self, backend_keys):
        self.ensure_one()
        _logger.debug("SEARCH: backend_keys = %s" % backend_keys)
        data = super(ResPartner, self)._update_search_data(backend_keys)
        backend_data = self._comchain_backend()
        for backend_key in backend_keys:
            if backend_key.startswith("comchain:") and backend_data:
                data[backend_key] = [backend_data.comchain_id]
        _logger.debug("SEARCH: data %s" % data)
        return data

    def _get_backend_credentials(self):
        self.ensure_one()
        data = super(ResPartner, self)._get_backend_credentials()
        backend_data = self._comchain_backend()
        data.extend(backend_data.comchain_backend_accounts_data)
        return data

    def backends(self):
        self.ensure_one()
        backends = super(ResPartner, self).backends()
        backend_data = self._comchain_backend()
        if not backend_data.comchain_id:
            return backends
        backend_id = backend_data.comchain_backend_id
        if not backend_id:
            ## not present in wallet and not configured in general settings
            return backends
        return backends | {backend_id}

    @api.multi
    def activateComchainUser(self, params):
        self.ensure_one()
        backend_data = self._comchain_backend()
        backend_data.write(
            {
                "comchain_status": "active",
                "comchain_type": "%s" % params.type,
                "comchain_credit_min": params.credit_min,
                "comchain_credit_max": params.credit_max,
            }
        )

    @api.multi
    def comchainCreateOrder(self, comchain_address, amount):
        order = self.env["sale.order"]
        line = self.env["sale.order.line"]
        comchain_product = self.env.ref("lcc_comchain_base.product_product_comchain")
        _logger.debug("PARTNER IN SELF?: %s(%s)" % (self.name, self.id))
        for partner in self:
            # TODO: case with contact of a company ?
            order_vals = {
                "partner_id": partner.id,
            }
            order_vals = order.play_onchanges(order_vals, ["partner_id"])
            _logger.debug("COMCHAIN ORDER: %s" % order_vals)
            order_id = order.create(order_vals)
            line_vals = {
                "order_id": order_id.id,
                "product_id": comchain_product.id,
            }
            line_vals = line.play_onchanges(line_vals, ["product_id"])
            line_vals.update(
                {
                    "product_uom_qty": amount,
                    "price_unit": 1,
                    # TODO: Taxes ?
                }
            )
            _logger.debug("COMCHAIN ORDER LINE: %s" % line_vals)
            line.create(line_vals)
            order_id.write(
                {"state": "sent", "require_signature": False, "require_payment": True}
            )
        return order_id

    def show_app_access_buttons(self):
        # For comchain the app access buttons on the portal are always displayed
        # as long as the comchain currency is defined,
        # as the user needs to connect to Monujo to create its wallet
        res = super(ResPartner, self).show_app_access_buttons()
        if self.env.user.company_id.comchain_currency_name:
            res = True
        return res
