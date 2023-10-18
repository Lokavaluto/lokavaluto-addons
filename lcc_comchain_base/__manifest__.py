{
    "name": "lcc_comchain_base",
    "summary": """
        comchain models and api for comchain transaction backend
        """,
    "description": """
   ::image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=================
lcc_comchain_base
=================

Base models and logics using comchain as transaction provider for numeric local complementary currency
It's part of Lokavaluto Project (https://lokavaluto.fr)

Installation
============

Just install lcc_comchain_base, all dependencies
will be installed by default.

TODO: Configuration -> ...

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
    "version": "12.0.2.4.0",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "lcc_lokavaluto_app_connection",
        "lcc_members",
        "onchange_helper",
    ],
    # always loaded
    "data": [
        "security/ir_rule.xml",
        "views/res_config_settings_view.xml",
        "views/lcc_backend.xml",
        "views/account_invoice_view.xml",
        "data/comchain_data.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
}
