import json
from odoo import models, fields, api


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
    )
    comchain_credit_min = fields.Float(string="Min Credit limit")
    comchain_credit_max = fields.Float(string="Max Credit limit")
    comchain_message_key = fields.Char(string="Message keys")

    @property
    def comchain_wallet_parsed(self):
        return json.loads(self.comchain_wallet) if self.comchain_wallet else {}

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
