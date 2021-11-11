# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "lcc_members",
    "version": "12.0.2.0.3",
    "author": "Lokavaluto",
    "maintainer": "False",
    "website": "False",
    "license": "",
    "category": "False",
    "summary": "Add new members app for local complementary currency management",
    "description": """
.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===========
lcc_members
===========

This module add new members apps with functionnality for local complementary currency organization.
It's part of Lokavaluto Project (https://lokavaluto.fr)

Installation
============

Just install lcc_members, all dependencies will be installed by default.

Known issues / Roadmap
======================

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/Lokavaluto/lokavaluto-addons/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* Lokavaluto: `Icon <https://lokavaluto.fr/web/image/res.company/1/logo?unique=f3db262>`_.

Contributors
------------

* Nicolas JEUDY <https://github.com/njeudy>
* Lokavaluto Teams

Funders
-------

The development of this module has been financially supported by:

* Lokavaluto (https://lokavaluto.fr)
* Mycéliandre (https://myceliandre.fr)

Maintainer
----------

This module is maintained by LOKAVALUTO.

LOKAVALUTO, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and ecosystem for local complementary currency organizations.

""",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "partner_firstname",
        "partner_industry_secondary",
        "partner_contact_in_several_companies",
        "membership",
        "complementary_contact_data",
        "base_address_city",
        "base_geolocalize",
        "base_location",
        "contract",
        "l10n_fr_siret",
        "event",
        "website",
        "crm",
        "website_partner",
        "l10n_fr",
        "sale",
        "partner_favorite",
    ],
    "external_dependencies": {
        "python": [],
    },
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "views/blank_card_menus.xml",
        "views/configuration_menus.xml",
        "views/res_partner_view.xml",
        "views/member_type_view.xml",
        "views/website_partner_view.xml",
        "views/assets.xml",
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
