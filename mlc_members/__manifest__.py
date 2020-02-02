# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'test',
    'version': '12.0.1.0.3',
    'author': 'Lokavaluto',
    'maintainer': 'False',
    'website': 'False',
    'license': '',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml # noqa
    # for the full list
    'category': 'False',    'summary': 'test',
    'description': """
.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==============
{module_title}
==============

This module extends the functionality of ... to support ...
and to allow you to ...

Installation
============

To install this module, you need to:

#. Do this ...

Configuration
=============

To configure this module, you need to:

#. Go to ...

.. figure:: path/to/local/image.png
   :alt: alternative description
   :width: 600 px

Usage
=====

To use this module, you need to:

#. Go to ...

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/{repo_id}/{branch}

.. repo_id is available in https://github.com/OCA/maintainer-tools/blob/master/tools/repos_with_ids.txt
.. branch is "8.0" for example

Known issues / Roadmap
======================

* Add ...

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/{project_repo}/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Firstname Lastname <email.address@example.org>
* Second Person <second.person@example.org>

Funders
-------

The development of this module has been financially supported by:

* Company 1 name
* Company 2 name

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.

""",

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'partner_firstname',
        'partner_industry_secondary',
        'membership',
        'complementary_contact_data',
        'base_address_city',
        'base_geolocalize',
        'base_location',
        'contract',
        'l10n_fr_siret',
        'event',
        'website',
        'calendar',
        'crm',
        'website_partner',
        'l10n_fr_siret',
        'sales_team',
        'l10n_fr',
	    'account',
	    'sale',
        'project',
    ],
    'external_dependencies': {
        'python': [],
    },

    # always loaded
    'data': [
        'views/res_partner_view.xml',
        'views/member_type_view.xml',
        'views/ir_ui_menus.xml',
        'views/report_membership_menus.xml',
        'views/product_template_menus.xml',
        'views/member_type_menus.xml',
        'views/res_partner_menus.xml',
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
