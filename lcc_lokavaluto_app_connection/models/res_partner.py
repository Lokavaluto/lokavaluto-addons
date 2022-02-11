from odoo import models, fields

import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Inherits partner and adds Tasks information in the partner form"""

    _inherit = "res.partner"

    in_mobile_app = fields.Boolean("In the mobile map", default=False)

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

    def domains_is_unvalidated_currency_backend(self):
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
