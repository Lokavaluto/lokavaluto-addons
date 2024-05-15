# Copyright 20204 Boris Gallet ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "lcc_fss_base",
    "version": "16.0.1.0.0",
    "author": "Elabore",
    "website": "https://elabore.coop",
    "maintainer": "Boris Gallet",
    "license": "AGPL-3",
    "category": "Tools",
    "summary": "base module for food social security projects",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "hr_professional_category",
       # "lcc_credit_requests_from_contracts",
       # "lcc_lokavaluto_app_connection",
        "lcc_members",
        "lcc_members_portal",
        "partner_contact_gender",
    ],
    "qweb": [],
    "external_dependencies": {
        "python": [],
    },
    # always loaded
    "data": [
        "views/res_partner_view.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
    "js": [],
    "css": [],
    "installable": True,
    # Install this module automatically if all dependency have been previously
    # and independently installed.  Used for synergetic or glue modules.
    "auto_install": False,
    "application": False,
}