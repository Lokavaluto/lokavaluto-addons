# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "lcc_members",
    "version": "12.0.4.1.0",
    "author": "Lokavaluto",
    "maintainer": "False",
    "website": "False",
    "license": "",
    "category": "False",
    "summary": "Add new members app for local complementary currency management",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "partner_firstname",
        "partner_industry_secondary",
        "partner_profiles",
        "partner_profiles_portal",
        "membership",
        "complementary_contact_data",
        "base_address_city",
        "base_geolocalize",
        "base_location",
        "contract",
        "event",
        "website",
        "crm",
        "website_partner",
        "l10n_fr",
        "sale",
        "partner_favorite",
        "portal",
        "web_m2x_options",
    ],
    "external_dependencies": {
        "python": [],
    },
    # always loaded
    "data": [
        "security/members_security.xml",
        "security/ir.model.access.csv",
        "views/blank_card_menus.xml",
        "views/configuration_menus.xml",
        "views/crm_team_view.xml",
        "views/res_partner_view.xml",
        "views/member_type_view.xml",
        "views/membership_lines.xml",
        "views/website_partner_view.xml",
        "views/assets.xml",
        "views/profile_portal_templates.xml",
        "views/invoice_portal_templates.xml",
        "views/res_users_views.xml",
        "wizard/membership_invoice_views.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
    "js": [],
    "css": [],
    "qweb": [],
    "installable": True,
    # Install this module automatically if all dependency have been previously
    # and independently installed.  Used for synergetic or glue modules.
    "auto_install": False,
    "application": False,
}
