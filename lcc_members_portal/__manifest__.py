# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "lcc_members_portal",
    "version": "12.0.1.6.3",
    "author": "Lokavaluto",
    "maintainer": "False",
    "website": "False",
    "license": "",
    "category": "False",
    "summary": "Add membership registration process on portal",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "lcc_members",
        "crm",
        "portal",
        "product",
        "membership",
        "website_sale",
        "crm",
    ],
    "external_dependencies": {
        "python": [],
    },
    # always loaded
    "data": [
        "data/crm_lead_tag_data.xml",
        "views/portal_my_home.xml",
        "views/portal_private_registration.xml",
        "views/portal_organization_registration.xml",
        "views/website_organization_registration.xml",
        "views/portal_organization_renewal.xml",
        "views/portal_affiliation_request.xml",
        "views/product_template_view.xml",
        "views/crm_lead_view.xml",
        "views/auth_signup_login_template.xml",
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
