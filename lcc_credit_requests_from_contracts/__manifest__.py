# Copyright 2024 Elabore
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "lcc_credit_requests_from_contracts",
    "version": "12.0.1.0.0",
    "author": "Elabore",
    "website": "https://elabore.coop",
    "maintainer": "Stéphan Sainléger",
    "license": "AGPL-3",
    "category": "Tools",
    "summary": "Generate lcc credit requests from contracts",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "contract",
        "lcc_lokavaluto_app_connection",
    ],
    "qweb": [],
    "external_dependencies": {
        "python": [],
    },
    # always loaded
    "data": [
        "views/contract.xml",
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
