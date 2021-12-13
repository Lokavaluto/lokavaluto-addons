# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import re
from odoo import http, tools, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class CustomerPortal(CustomerPortal):
    PROFILE_FIELDS = [
        "nickname",
        "function",
        "phone",
        "mobile",
        "email",
        "website_url",
        "street",
        "street2",
        "city",
        "country_id",
        "zipcode",
        "website_description",
        "industry_id",
        "detailed_activity",
        "reasons_choosing_mlc",
        "itinerant",
        "accept_coupons",
        "accept_digital_currency",
        "phone_pro",
        "opening_time",
        "discount",
    ]

    def _get_domain_my_profiles(self, user):
        return [("contact_id", "=", user.partner_id.id), ("active", "=", True)]

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values["profile_count"] = request.env["res.partner"].search_count(
            self._get_domain_my_profiles(request.env.user)
        )
        return values

    def _profile_get_page_view_values(self, profile, access_token, **kwargs):
        values = {
            "page_name": "profile",
            "profile": profile,
        }
        return self._get_page_view_values(
            profile, access_token, values, "my_profiles_history", False, **kwargs
        )

    def _details_profile_form_validate(self, data, profile_id):
        error = dict()
        error_message = []

        # nickname uniqueness
        if data.get("nickname") and request.env["res.partner"].search(
            [
                ("name", "=", data.get("nickname")),
                ("partner_profile.ref", "=", "parter_profile_public"),
                ("id", "!=", profile_id),
            ]
        ):
            error["name"] = "error"
            error_message.append(
                _("This nickname is already used, please find an other idea.")
            )

        # email validation
        if data.get("email") and not tools.single_email_re.match(data.get("email")):
            error["email"] = "error"
            error_message.append(
                _("Invalid Email! Please enter a valid email address.")
            )

        return error, error_message

    @http.route(
        ["/my/profiles", "/my/profiles/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_profiles(
        self, page=1, date_begin=None, date_end=None, sortby=None, **kw
    ):
        values = self._prepare_portal_layout_values()
        profile = request.env["res.partner"]
        domain = self._get_domain_my_profiles(request.env.user)

        searchbar_sortings = {
            "name": {"label": _("Name"), "order": "name"},
            "partner_profile": {"label": _("Profile Type"), "order": "partner_profile"},
            "parent_id": {"label": _("Company"), "order": "parent_id"},
        }
        if not sortby:
            sortby = "name"
        order = searchbar_sortings[sortby]["order"]

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups("res.partner", domain)

        # profiles count
        profile_count = profile.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/profiles",
            url_args={"sortby": sortby},
            total=profile_count,
            page=page,
            step=self._items_per_page,
        )

        # content according to pager and archive selected
        profiles = profile.search(
            domain, order=order, limit=self._items_per_page, offset=pager["offset"]
        )
        request.session["my_profiles_history"] = profiles.ids[:100]

        values.update(
            {
                "profiles": profiles,
                "page_name": "profile",
                "archive_groups": archive_groups,
                "default_url": "/my/profiles",
                "pager": pager,
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
            }
        )
        return request.render("lcc_members.portal_my_profiles", values)

    @http.route(
        ["/my/profile/<int:profile_id>", "/my/profile/save"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_profile(
        self, profile_id=None, access_token=None, redirect=None, **kw
    ):
        # The following condition is to transform profile_id to an int, as it is sent as a string from the templace "portal_my_profile"
        # TODO: find a better way to retrieve the profile_id at form submit step
        if not isinstance(profile_id, int):
            profile_id = int(profile_id)

        # Check that the user has the right to see this profile
        try:
            profile_sudo = self._document_check_access(
                "res.partner", profile_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my/profiles")

        values = self._profile_get_page_view_values(profile_sudo, access_token, **kw)
        values.update(
            {
                "error": {},
                "error_message": [],
            }
        )

        if kw and request.httprequest.method == "POST":
            # the user has clicked in the Save button to save new data
            error, error_message = self._details_profile_form_validate(kw, profile_id)
            values.update({"error": error, "error_message": error_message})
            values.update(kw)
            if not error:
                values = {key: kw[key] for key in self.PROFILE_FIELDS if key in kw}
                values.update({"lastname": values.pop("nickname", "")})
                values.update({"zip": values.pop("zipcode", "")})
                values.update({"website": values.pop("website_url", "")})
                profile = request.env["res.partner"].browse(profile_id)
                profile.sudo().write(values)
                if redirect:
                    return request.redirect(redirect)
                return request.redirect("/my/profiles")
        else:
            # This is just the form page opening. We send all the data needed for the form fields
            countries = request.env["res.country"].sudo().search([])
            industries = request.env["res.partner.industry"].sudo().search([])
            values.update(
                {
                    "profile_id": profile_id,  # Sent in order to retrieve it at submit time
                    "countries": countries,
                    "industries": industries,
                    "redirect": redirect,
                }
            )
            return request.render("lcc_members.portal_my_profile", values)
