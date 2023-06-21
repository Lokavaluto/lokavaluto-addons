from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)


class ResPartnerBackend(models.Model):
    """Add backend commom property for local currency"""

    _name = "res.partner.backend"

    type = fields.Selection([], string="Type", required=True)
    name = fields.Char("Name", required=True)
    partner_public_name = fields.Char("Partner Public Name",
        store=True,
        compute="_compute_partner_name",
    )
    status = fields.Selection(
        [
            ("inactive", "Inactive"),
            ("to_confirm", "To Confirm"),
            ("active", "Active"),
            ("blocked", "Blocked"),
        ],
        string="Status",
        store=True,
        compute="_compute_status",
    )
    partner_id = fields.Many2one("res.partner", string="Partner", required=True)

    @api.depends("name", "type")
    def _compute_status(self):
        pass

    @api.depends('partner_id.public_profile_id', 'partner_id.public_profile_id.name')
    def _compute_partner_name(self):
        for record in self:
            if record.partner_id.public_profile_id:
                record.partner_public_name = record.partner_id.public_profile_id.name


class ResPartner(models.Model):
    """Inherits partner and adds Tasks information in the partner form"""

    _inherit = "res.partner"

    in_mobile_app = fields.Boolean("In the mobile map", default=False)
    lcc_backend_ids = fields.One2many(
        "res.partner.backend", "partner_id", string="Local Currency Wallets"
    )
    app_exported_fields = []

    def _get_mobile_app_pro_domain(self, bounding_box, categories):
        if categories:
            return [
                ("in_mobile_app", "=", True),
                ("is_company", "=", True),
                ("industry_id", "in", categories),
                ("partner_longitude", "!=", float()),
                ("partner_latitude", "!=", float()),
                ("partner_longitude", ">", float(bounding_box.minLon)),
                ("partner_longitude", "<", float(bounding_box.maxLon)),
                ("partner_latitude", ">", float(bounding_box.minLat)),
                ("partner_latitude", "<", float(bounding_box.maxLat)),
            ]
        else:
            return [
                ("in_mobile_app", "=", True),
                ("is_company", "=", True),
                ("partner_longitude", "!=", float()),
                ("partner_latitude", "!=", float()),
                ("partner_longitude", ">", float(bounding_box.minLon)),
                ("partner_longitude", "<", float(bounding_box.maxLon)),
                ("partner_latitude", ">", float(bounding_box.minLat)),
                ("partner_latitude", "<", float(bounding_box.maxLat)),
            ]

    def in_mobile_app_button(self):
        """Inverse the value of the field ``in_mobile_app``
        for the current instance."""
        self.in_mobile_app = not self.in_mobile_app

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
