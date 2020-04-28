{
    "name": "lcc_members_search",
    "summary": """
        Module to search easily contacts from members module""",
    "description": """
        Module to search easily contacts from members module,
    """,
    "author": "lokavaluto",
    "website": "http://www.lokavaluto.fr",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "Uncategorized",
    "version": "12.0.1.0.10",
    # any module necessary for this one to work correctly
    "depends": ["base"],
    # always loaded
    "data": [
        # 'security/ir.model.access.csv',
        "views/templates.xml",
    ],
}
