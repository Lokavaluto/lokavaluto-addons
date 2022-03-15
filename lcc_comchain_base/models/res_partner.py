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


class ResPartner(models.Model):
    """Inherits partner:
    - add comchain fields in the partner form
    - add functions"""

    _inherit = "res.partner"

    comchain_active = fields.Boolean(string="comchain OK")
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

    def _update_auth_data(self, password):
        self.ensure_one()
        data = super(ResPartner, self)._update_auth_data(password)
        data.extend(self._comchain_backend_json_data())
        # Addition of user's organizations' backends
        if self.other_contact_ids:
            # The user has positions in one or several organizations
            for position_partner in self.other_contact_ids:
                if position_partner.manage_structure_wallet:
                    structure = position_partner.parent_id
                    if structure._comchain_backend():
                        data.extend(
                            position_partner.parent_id._comchain_backend_json_data()
                        )
        return data

    def _comchain_backend(self):
        # We only support one backend per type for now
        backend_data = self.env["res.partner.backend"]
        if self.lcc_backend_ids.filtered(lambda r: r.type == "comchain"):
            backend_data = self.lcc_backend_ids.filtered(
                lambda r: r.type == "comchain"
            )[0]
        return backend_data

    @property
    def _comchain_wallet(self):
        backend_data = self._comchain_backend()
        return (
            json.loads(backend_data.comchain_wallet)
            if backend_data.comchain_wallet
            else {}
        )

    @property
    def _comchain_backend_id(self):
        """Return the technical id for the backend"""
        wallet = self._comchain_wallet
        currency_name = (
            wallet.get("server", {}).get("name", {})
            or self.env.user.company_id.comchain_currency_name
        )
        if not currency_name:
            ## not present in wallet and not configured in general settings
            return False
        return "%s:%s" % ("comchain", currency_name)

    def _comchain_backend_json_data(self):
        """Prepare backend data to be sent by credentials requests"""

        backend_data = self._comchain_backend()
        backend_id = self._comchain_backend_id
        if not backend_id:
            ## not present in wallet and not configured in general settings
            return []

        data = {"type": backend_id, "accounts": []}
        wallet = self._comchain_wallet
        if wallet:
            data["accounts"].append(
                {
                    "wallet": wallet,
                    "message_key": backend_data.comchain_message_key,
                    "active": backend_data.status == "active",
                }
            )
        return [data]

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
        data.extend(self._comchain_backend_json_data())
        return data

    def domains_is_unvalidated_currency_backend(self):
        parent_domains = super(
            ResPartner, self
        ).domains_is_unvalidated_currency_backend()
        parent_domains[self._comchain_backend_id] = [
            ("lcc_backend_ids.status", "=", "to_confirm"),
            ("lcc_backend_ids.type", "=", "comchain"),
            ("lcc_backend_ids.comchain_id", "!=", False),
        ]
        return parent_domains

    def backends(self):
        self.ensure_one()
        backends = super(ResPartner, self).backends()
        backend_data = self._comchain_backend()
        if backend_data.comchain_id:
            wallet = self._comchain_wallet()
            currency_name = (
                wallet.get("server", {}).get("name", {})
                or self.env.user.company_id.comchain_currency_name
            )
            if not currency_name:
                ## not present in wallet and not configured in general settings
                return backends
            return backends | {"%s:%s" % (backend_data.type, currency_name)}
        else:
            return backends

    @api.multi
    def activateComchainUser(self, params):
        self.ensure_one()
        backend_data = self._comchain_backend()
        backend_data.write(
            {
                "status": "active",
                "comchain_status": "actif",
                "comchain_type": "%s" % params.type,
                "comchain_credit_min": params.credit_min,
                "comchain_credit_max": params.credit_max,
            }
        )
