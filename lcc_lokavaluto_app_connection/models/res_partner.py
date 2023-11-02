from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Inherits partner and adds Tasks information in the partner form"""

    _inherit = "res.partner"

    lcc_backend_ids = fields.One2many(
        "res.partner.backend", "partner_id", string="Local Currency Wallets"
    )
    nb_wallets = fields.Integer(
        "Nb Wallets", readonly=True, compute="_compute_nb_wallets"
    )
    nb_wallets_to_confirm = fields.Integer(
        "Nb Wallets to confirm", readonly=True, compute="_compute_nb_wallets"
    )
    nb_wallets_inactive = fields.Integer(
        "Nb Wallets inactive", readonly=True, compute="_compute_nb_wallets"
    )
    nb_wallets_blocked = fields.Integer(
        "Nb Wallets blocked", readonly=True, compute="_compute_nb_wallets"
    )
    app_exported_fields = []

    @api.one
    @api.depends("lcc_backend_ids")
    def _compute_nb_wallets(self):
        self.nb_wallets = len(self.lcc_backend_ids)
        self.nb_wallets_to_confirm = len(
            self.lcc_backend_ids.filtered(lambda x: x.status == "to_confirm")
        )
        self.nb_wallets_inactive = len(
            self.lcc_backend_ids.filtered(lambda x: x.status == "inactive")
        )
        self.nb_wallets_blocked = len(
            self.lcc_backend_ids.filtered(lambda x: x.status == "blocked")
        )

    def get_wallets(self, type):
        self.ensure_one()
        wallets = [backend for backend in self.lcc_backend_ids if backend.type == type]
        if len(wallets) > 0:
            return wallets
        else:
            return None

    @api.multi
    def create_numeric_lcc_order(self, wallet_id, amount):
        order = self.env["sale.order"]
        line = self.env["sale.order.line"]
        lcc_product = wallet_id.get_lcc_product()
        _logger.debug("PARTNER IN SELF?: %s(%s)" % (self.name, self.id))
        for partner in self:
            order_vals = {
                "partner_id": partner.id,
                "user_id": 2,  # OdooBot-s ID
            }
            order_vals = order.play_onchanges(order_vals, ["partner_id"])
            _logger.debug("NUMERIC LCC ORDER: %s" % order_vals)
            order_id = order.create(order_vals)
            line_vals = {
                "order_id": order_id.id,
                "product_id": lcc_product.id,
            }
            line_vals = line.play_onchanges(line_vals, ["product_id"])
            line_vals.update(
                {
                    "product_uom_qty": amount,
                    "price_unit": 1,
                }
            )
            _logger.debug("NUMERIC LCC ORDER LINE: %s" % line_vals)
            line.create(line_vals)
            order_id.write(
                {"state": "sent", "require_signature": False, "require_payment": True}
            )
        return order_id

    def _update_auth_data(self, password):
        return []

    def _get_backend_credentials(self):
        return []

    def _update_search_data(self, backend_keys):
        return {}

    def backends(self):
        return set()

    def _validator_return_authenticate(self):
        return {
            "uid": {"type": "integer"},
            "status": {"type": "string", "required": True},
            "error": {"type": "string"},
            "prefetch": {"type": "dict"},
            "api_token": {"type": "string"},
            "api_version": {"type": "integer"},
        }

    @api.multi
    def open_commercial_member_entity(self):
        """Utility method used to add an "Open Company" button in partner views"""
        self.ensure_one()
        partner_form_id = self.env.ref("base.view_partner_form").id
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "view_mode": "form",
            "views": [(partner_form_id, "form")],
            "res_id": self.commercial_partner_id.id,
            "target": "current",
            "flags": {"form": {"action_buttons": True}},
        }

    def show_app_access_buttons(self):
        return False

    @api.multi
    def lcc_profile_info(self):
        res = []
        for partner in self:
            profile_info = partner.public_profile_id.jsonify(
                [
                    "name",
                    "street",
                    "street2",
                    "zip",
                    "city",
                    "mobile",
                    "email",
                    "phone",
                    ("country_id", ["id", "name"]),
                ]
            )[0]
            profile_info.update(
                {
                    "id": partner.id,
                    "is_favorite": partner.is_favorite,
                    "public_name": partner.public_name,
                }
            )
            res.append(profile_info)
        return res
