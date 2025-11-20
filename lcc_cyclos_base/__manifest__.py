{
    "name": "lcc_cyclos_base",
    "summary": """
        Cyclos models and api for cyclos transaction backend
        """,
    "author": "Lokavaluto",
    "website": "https://lokavaluto.fr",
    "category": "Website",
    "version": "16.0.1.2.0",
    "licence": "AGPL-3",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "lcc_lokavaluto_app_connection",
        "lcc_members",
        "auth_oauth",
    ],
    # always loaded
    "data": [
        "security/ir_rule.xml",
        "security/ir.model.access.csv",
        "wizards/create_cyclos_wallet_wizard.xml",
        "views/res_alt_currency.xml",
        "views/res_partner_view.xml",
        "views/wallet.xml",
        "data/cyclos_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "lcc_cyclos_base/static/src/scss/signup.scss",
        ],
    },
    # only loaded in demonstration mode
    "demo": [],
}
