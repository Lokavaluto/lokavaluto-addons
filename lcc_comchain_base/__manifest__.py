{
    "name": "lcc_comchain_base",
    "summary": """
        comchain models and api for comchain transaction backend
        """,
    "author": "Lokavaluto",
    "website": "https://lokavaluto.fr",
    "category": "Website",
    "version": "16.0.1.0.0",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "lcc_lokavaluto_app_connection",
        "lcc_members",
    ],
    # always loaded
    "data": [
        "security/ir_rule.xml",
        "views/res_config_settings_view.xml",
        "views/lcc_backend.xml",
        "data/comchain_data.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
}
