{
    "name": "lcc_lokavaluto_app_connection",
    "summary": "REST Odoo Backend for Lokavaluto mobile application",
    "author": "Lokavaluto",
    "website": "https://lokavaluto.fr",
    "category": "Website",
    "version": "12.0.2.1.1",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "sale",
        "base_rest",
        "auth_api_key",
        "base_rest_datamodel",
        "base_jsonify",
        "partner_favorite",
        "lcc_members",
        "lcc_members_portal",
        "lcc_members_qr",
        "partner_profiles_portal",
        "membership",
    ],
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "views/lcc_app_connection_partner.xml",
        "views/lcc_backend.xml",
        "views/menu.xml",
        "views/portal_my_home.xml",
        "views/res_config_settings_view.xml",
        "views/portal_private_registration.xml",
        "views/portal_organization_registration.xml",
        "views/website_organization_registration.xml",
        "views/crm_lead_view.xml",
        "data/numeric_data.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
}
