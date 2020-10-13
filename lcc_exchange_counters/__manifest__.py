# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'lcc_exchange_counters',
    'version': '12.0.1.0.10',
    'author': 'Lokavaluto',
    'maintainer': 'False',
    'website': 'https://lokavaluto.fr',
    'license': '',
    'category': 'False',
    'summary': 'Manage all the transactions of a local complementary currency''s exchange counter',
    'description': """
.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==========================
lcc_exchange_counters
==========================

Exchange counter module for managing local complementary currency's physical transactions:
    - conversions
    - reverse conversions
    - monney transfers between offices
    - statistics
It's part of Lokavaluto Project (https://lokavaluto.fr)

Installation
============

Just install lcc_exchange_counters, all dependencies will be installed by default.

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
    'depends': [
        'base', 
        'point_of_sale',
        'stock',
        'stock_account',
    ],
    'external_dependencies': {
        'python': [],
    },

    # always loaded
    'data': [
        'security/exchange_counters_security.xml',
        'security/ir.model.access.csv',
        'views/exchange_counters_config_view.xml',
        'views/exchange_counters_inventory_view.xml',
        'views/exchange_counters_menu.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
    ],

    'js': [],
    'css': [],
    'qweb': [],

    'installable': True,
    # Install this module automatically if all dependency have been previously
    # and independently installed.  Used for synergetic or glue modules.
    'auto_install': False,
    'application': False,
}