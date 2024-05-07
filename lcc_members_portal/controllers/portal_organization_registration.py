# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class PortalOrganizationRegistration(CustomerPortal):
    _ORGANIZATION_REGISTRATION_FIELDS = [
        "company_name",
        "business_name",
        "website_description",
        "street",
        "street2",
        "city",
        "zipcode",
        "country_id",
        # "team_id",  # TODO: issue occuring when this field is added. INVESTIGATION NEEDED
        "phone",
        "company_email",
        "website_url",
        "industry_id",
        "detailed_activity",
        "reasons_choosing_mlc",
        "opening_time",
        "discount",
        "function",
        "email_pro",
        "phone_pro",
        "message_from_candidate",
    ]

    # Variable to update to add other fields in child classes
    _EXTRA_FIELDS = []

    def _organization_get_page_view_values(self, partner, access_token, **kwargs):
        values = {
            "page_name": "portal_organization_registration",
            "partner": partner,
        }
        return self._get_page_view_values(
            partner,
            access_token,
            values,
            "my_organization_registration_history",
            False,
            **kwargs
        )

    def get_organization_membership_product(self):
        product_obj = request.env["product.template"]
        product = product_obj.sudo().get_organization_membership_product(
            request.env.user.partner_id.company_id.id
        )
        return product

    def _get_selected_team_id(self, partner):
        if len(request.env["res.company"].sudo().search([])) > 1:
            return (
                request.env["crm.team"]
                .sudo()
                .search(
                    [
                        ("local_group", "=", True),
                        ("company_id", "=", partner.company_id.id),
                    ]
                )
            )
        else:
            return request.env["crm.team"].sudo().search([("local_group", "=", True)])

    @http.route(
        ["/my/organization_registration"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_organization_registration(self, access_token=None, redirect=None, **kw):
        partner = request.env.user.partner_id

        values = self._organization_get_page_view_values(partner, access_token, **kw)
        product = self.get_organization_membership_product()
        titles = request.env["res.partner.title"].sudo().search([])
        countries = request.env["res.country"].sudo().search([])
        teams = self._get_selected_team_id(partner)
        industries = request.env["res.partner.industry"].sudo().search([])
        error = dict()
        error_message = []

        values.update(
            {
                "product": product,
                "total_membership": product.list_price,
                "dynamic_price": product.dynamic_price,
                "titles": titles,
                "countries": countries,
                "industries": industries,
                "teams": teams,
                "error": error,
                "error_message": error_message,
            }
        )
        return request.render(
            "lcc_members_portal.portal_organization_registration", values
        )

    def _compute_organization_form_data(self, data):
        partner = request.env.user.partner_id
        values = {
            "partner_id": partner.id,
            "company_id": partner.company_id.id,
            "type": "opportunity",
            "lead_type": "membership_web_application",
            "accept_coupons": data.get("accept_coupons", "off") == "on",
            "accept_digital_currency": data.get("accept_digital_currency", "off")
            == "on",
            "itinerant": data.get("itinerant", "off") == "on",
            "refuse_numeric_wallet_creation": data.get("refuse_numeric_wallet_creation", "off") == "on",
            "want_newsletter_subscription": data.get(
                "want_newsletter_subscription", "off"
            )
            == "on",
            "accept_policy": data.get("accept_policy", "off") == "on",
            "tag_ids": [
                (
                    4,
                    request.env.ref("lcc_members_portal.categ_oppor_application").id,
                    None,
                )
            ],
        }

        if float(data.get("total_membership", False)):
            values["total_membership"] = float(data.get("total_membership"))
        else:
            values[
                "total_membership"
            ] = self.get_organization_membership_product().list_price

        for field in self._ORGANIZATION_REGISTRATION_FIELDS:
            if data.get(field):
                values[field] = data.pop(field)
        for field in self._EXTRA_FIELDS:
            if data.get(field):
                values[field] = data.pop(field)

        values["name"] = values["company_name"]
        values.update({
            "zip": values.pop("zipcode", ""),
            "website": values.pop("website_url", "")
        })

        return values

    @http.route(
        ["/membership/send_request"],
        type="http",
        auth="public",
        website=True,
    )
    def send_registration_request(self, **kwargs):
        # Create a new lead
        values = self._compute_organization_form_data(kwargs)
        lead = request.env["crm.lead"].sudo().create(values)
        lead.team_id = request.env["crm.team"].browse(kwargs.pop(
            "team_id"
        ))  # TODO: see remark above concerning team_id
        return request.render(
            "lcc_members_portal.portal_organization_registration_saved", {}
        )
