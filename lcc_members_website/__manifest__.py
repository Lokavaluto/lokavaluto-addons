# Copyright 2020-2021 Lokavaluto
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "LCC Members Website",
    "version": "12.0.1.0.1",
    "depends": ["lcc_members", "website", "partner_contact_gender"],
    "author": "Lokavaluto",
    "category": "Website",
    "website": "https://lokavaluto.fr",
    "license": "AGPL-3",
    "summary": """
    This module adds the members subscription form
    allowing to subscribe online.
    """,
    "data": [
        "views/membership_template.xml",
        "data/website_member_data.xml",
        "views/product_template_view.xml",
    ],
    "installable": True,
    "application": True,
}
