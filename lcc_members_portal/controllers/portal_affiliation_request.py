# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class PortalOrganizationRegistration(CustomerPortal):
    _AFFILIATION_REQUEST_FIELDS = [
        "company_name",
        "function",
        "phone_pro",
        "message_from_candidate",
    ]

    # Variable to update to add other fields in child classes
    _EXTRA_FIELDS = []

    def _affiliation_get_page_view_values(self, partner, access_token, **kwargs):
        values = {
            "page_name": "portal_affiliation_request",
            "partner": partner,
        }
        return self._get_page_view_values(
            partner,
            access_token,
            values,
            "my_affiliation_request_history",
            False,
            **kwargs
        )

    @http.route(
        ["/my/affiliation_request"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_affiliation_request(self, access_token=None, redirect=None, **kw):
        partner = request.env.user.partner_id

        values = self._affiliation_get_page_view_values(partner, access_token, **kw)
        error = dict()
        error_message = []

        values.update(
            {
                "error": error,
                "error_message": error_message,
            }
        )
        return request.render("lcc_members_portal.portal_affiliation_request", values)

    @http.route(
        ["/affiliation/send_request"],
        type="http",
        auth="public",
        website=True,
    )
    def send_affiliation_request(self, **kwargs):
        # Create a new lead
        values = {}
        for field in self._AFFILIATION_REQUEST_FIELDS:
            if kwargs.get(field):
                values[field] = kwargs.pop(field)
        for field in self._EXTRA_FIELDS:
            if kwargs.get(field):
                values[field] = kwargs.pop(field)
        partner = request.env.user.partner_id
        values["name"] = (
            "[AFFILIATION] " + partner.name + " in " + values["company_name"]
        )
        values["partner_id"] = partner.id
        values["type"] = "opportunity"
        values["lead_type"] = "affiliation_request"
        values["edit_structure_main_profile"] = (
            kwargs.get("manage_main_profile", "off") == "on"
        )
        values["edit_structure_public_profile"] = (
            kwargs.get("manage_public_profile", "off") == "on"
        )
        lead = request.env["crm.lead"].sudo().create(values)
        lead.team_id = partner.team_id
        return request.render("lcc_members_portal.portal_affiliation_request_saved", {})
