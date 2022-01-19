# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "lcc_members_portal",
    "version": "12.0.0.0.0",
    "author": "Lokavaluto",
    "maintainer": "False",
    "website": "False",
    "license": "",
    "category": "False",
    "summary": "Add membership registration process on portal",
    "description": """
   :image: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==================
lcc_members_portal
==================

This module add new members registration process from the portal space of a connected user.
It's part of Lokavaluto Project (https://lokavaluto.fr)

Installation
============

Just install lcc_members_portal, all dependencies will be installed by default.

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
* Stéphan SAINLÉGER <https://github.com/stephansainleger>
* Lokavaluto Teams

Funders
-------

The development of this module has been financially supported by:

* Lokavaluto (https://lokavaluto.fr)
* Mycéliandre (https://myceliandre.fr)
* Elabore (https://elabore.coop)

Maintainer
----------

This module is maintained by LOKAVALUTO.

LOKAVALUTO, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and ecosystem for local complementary currency organizations.

""",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "lcc_members",
        "crm",
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
        "views/portal_my_home.xml",
        "views/portal_private_registration.xml",
        "views/portal_oganization_registration.xml",
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
