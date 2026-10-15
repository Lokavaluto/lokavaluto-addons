{
    "name": "lcc_wallet_qr",
    "summary": "Generation of a QR code for LCC numeric wallets",
    "author": "Lokavaluto",
    "website": "https://lokavaluto.fr",
    "category": "Website",
    "version": "16.0.1.1.0",
    "licence": "AGPL-3",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "lcc_lokavaluto_app_connection",
    ],
    # always loaded
    "data": [
        "views/wallet.xml",
        "data/res_partner_backend_data.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
}
