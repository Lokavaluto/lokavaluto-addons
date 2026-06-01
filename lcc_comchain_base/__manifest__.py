{
    "name": "lcc_comchain_base",
    "summary": """
        comchain models and api for comchain transaction backend
        """,
    "author": "Lokavaluto",
    "website": "https://lokavaluto.fr",
    "category": "Website",
    "version": "16.0.1.3.1",
    "licence": "AGPL-3",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "lcc_lokavaluto_app_connection",
        "lcc_members",
    ],
    # always loaded
    "data": [
        "security/ir_rule.xml",
        "views/res_alt_currency.xml",
        "views/wallet.xml",
        "views/credit_request.xml",
        "data/comchain_data.xml",
        "data/res_alt_currency_data.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
}
