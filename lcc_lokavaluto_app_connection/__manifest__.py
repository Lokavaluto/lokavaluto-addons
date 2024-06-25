{
    "name": "lcc_lokavaluto_app_connection",
    "summary": "REST Odoo Backend for Lokavaluto mobile application",
    "author": "Lokavaluto",
    "website": "https://lokavaluto.fr",
    "category": "Website",
    "version": "16.0.1.0.0",
    # any module necessary for this one to work correctly
    "depends": [
        "auth_api_key",
        "auth_signup",
        "base",
        "base_rest",
        "base_rest_datamodel",
        "jsonifier",
        "lcc_members",
        "onchange_helper",
        "partner_favorite",
        "partner_profiles_portal",
        "sale",
    ],
    # always loaded
    "data": [
        "security/wallets_security.xml",
        "security/ir.model.access.csv",
        "wizards/create_credit_request.xml",
        "views/account_invoice.xml",
        "views/res_partner.xml",
        "views/sale_order.xml",
        "views/wallet.xml",
        "views/credit_request.xml",
        "views/debit_request.xml",
        "views/commission_rule.xml",
        "views/reconversion_rule.xml",
        "views/menu.xml",
        "views/portal_my_home.xml",
        "views/res_config_settings_view.xml",
        "data/numeric_data.xml",
        "data/res_company_data.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
}
