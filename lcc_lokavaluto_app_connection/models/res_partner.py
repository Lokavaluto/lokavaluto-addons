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

    def get_wallets_by_currency_type(self, type: str):
        self.ensure_one()
        wallets = [wallet for wallet in self.lcc_backend_ids if wallet.type == type]
        if len(wallets) > 0:
            if len(wallets) > 1:
                raise NotImplementedError(
                    "Several wallets retrieved - Multiwallet of one currency is not implemented yet"
                )
            return wallets
        else:
            return self.env["res.partner.backend"]

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

    def lcc_profile_info(self):
        res = []
        for partner in self:
            if not partner.public_profile_id:
                _logger.warning(
                    "Partner %s (id: %d) has no public profile id. Skipping.",
                    partner.name,
                    partner.id,
                )
                continue
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
                    "is_company",
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
        if not res and len(self) > 1:
            _logger.warning("No public profile found for any of the partners.")
        return res
