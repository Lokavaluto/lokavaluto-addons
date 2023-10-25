{
    "name": "lcc_wallet_qr",
    "summary": "Generation of a QR code for LCC numeric wallets",
    "author": "Lokavaluto",
    "website": "https://lokavaluto.fr",
    "category": "Website",
    "version": "12.0.1.0.0",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "lcc_lokavaluto_app_connection",
    ],
    # always loaded
    "data": [
        "views/lcc_backend.xml",
        "data/res_partner_backend_data.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
}
