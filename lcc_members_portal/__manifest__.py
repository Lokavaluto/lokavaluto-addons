# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "lcc_members_portal",
    "version": "16.0.1.0.0",
    "author": "Lokavaluto",
    "maintainer": "False",
    "website": "False",
    "license": "",
    "category": "False",
    "summary": "Add membership registration process on portal",
    # any module necessary for this one to work correctly
    "depends": [
        "account",
        "base",
        "crm",
        "lcc_members",
        "membership",
        "portal",
        "product",
        "website_sale",
    ],
    "external_dependencies": {
        "python": [],
    },
    # always loaded
    "data": [
        "data/crm_tag_data.xml",
        "views/portal_my_home.xml",
        "views/portal_private_registration.xml",
        "views/portal_organization_registration.xml",
        "views/website_organization_registration.xml",
        "views/portal_organization_renewal.xml",
        "views/portal_affiliation_request.xml",
        "views/product_template_view.xml",
        "views/crm_lead_view.xml",
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
