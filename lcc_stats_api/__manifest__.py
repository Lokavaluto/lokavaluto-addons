{
    "name": "lcc_stats_api",
    "summary": "REST Odoo Backend for getting stats about local complementary currency",
    "author": "Lokavaluto",
    "website": "https://lokavaluto.fr",
    "category": "Website",
    "version": "12.0.1.0.0",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "base_rest",
        "auth_api_key",
        "base_rest_datamodel",
        "membership",
        "lcc_lokavaluto_app_connection",
    ],
    # always loaded
    "data": [],
    # only loaded in demonstration mode
    "demo": [],
}
