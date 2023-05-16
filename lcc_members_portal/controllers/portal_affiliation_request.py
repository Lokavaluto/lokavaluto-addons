# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class PortalOrganizationAffiliation(CustomerPortal):
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

    def _compute_affiliation_form_data(self, data):
        partner = request.env.user.partner_id
        values = {
            "partner_id": partner.id,
            "type": "opportunity",
            "lead_type": "affiliation_request",
            "edit_structure_profiles": data.get("manage_structure_profilse", "off")
            == "on",
            "tag_ids": [(4, request.env.ref("lcc_members_portal.categ_oppor_affiliation").id, None)],
        }
        for field in self._AFFILIATION_REQUEST_FIELDS:
            if data.get(field):
                values[field] = data.pop(field)
        for field in self._EXTRA_FIELDS:
            if data.get(field):
                values[field] = data.pop(field)
        values["name"] =  values["company_name"]
        return values

    @http.route(
        ["/affiliation/send_request"],
        type="http",
        auth="public",
        website=True,
    )
    def send_affiliation_request(self, **kwargs):
        # Create a new lead
        values = self._compute_affiliation_form_data(kwargs)
        lead = request.env["crm.lead"].sudo().create(values)
        lead.team_id = request.env.user.partner_id.team_id
        return request.render("lcc_members_portal.portal_affiliation_request_saved", {})
