{
    "name": "lcc_lokavaluto_app_connection",
    "summary": """
        REST Odoo Backend for Lokavaluto mobile application
        """,
    "description": """
   ::image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=============================
lcc_lokavaluto_app_connection
=============================

Lokavaluto mobile application connection module, to communicate the Odoo
database data needed for the Local Currency mobile app
It's part of Lokavaluto Project (https://lokavaluto.fr)

Installation
============

Just install lcc_lokavaluto_app_connection, all dependencies
will be installed by default.

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

* Stéphan SAINLEGER <https://github.com/stephansainleger>
* Nicolas JEUDY <https://github.com/njeudy>
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
    "author": "Lokavaluto",
    "website": "https://lokavaluto.fr",
    "category": "Website",
    "version": "12.0.1.0.7",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "sale",
        "base_rest",
        "auth_api_key",
        "base_rest_datamodel",
        "base_jsonify",
        "partner_favorite",
        "lcc_members",
        "lcc_members_qr",
    ],
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "views/lcc_app_connection_partner.xml",
        "views/lcc_backend.xml",
        "data/numeric_data.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
}
