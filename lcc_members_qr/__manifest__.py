{
    "name": "lcc_members_qr",
    "summary": """
        Generation of a QR code for LCC members
        """,
    "description": """
   ::image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==============
lcc_members_qr
==============

Module to generate a QR code containing the partner's website_url
It's part of Lokavaluto Project (https://lokavaluto.fr)

Installation
============

Just install lcc_members_qr, all dependencies will be installed by default.

Configuration
=============

No configuration needed on this addon.

Usage
=====

To generate the QR code of a partner, go on the form view of the partner, anc click on the button "Generate QR". 
You will be able to download a pdf page containing the QR code, and you will find the PNG image in the "QR code" notebook page.

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
    "version": "12.0.1.0.6",
    # any module necessary for this one to work correctly
    "depends": ["base"],
    # always loaded
    "data": [
        "report/paperformat.xml",
        "report/report.xml",
        "views/qr_res_partner.xml",
        "report/template.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
}
