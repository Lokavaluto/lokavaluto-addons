{
    'name': "lcc_partner_gogocartojs",

    'summary': """
        REST Backend for gogocartojs library
        """,

    'description': """
        REST Backend for gogocartojs library
    """,

    'author': "Lokavaluto",
    'website': "https://lokavaluto.fr",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Website',
    'version': '12.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}