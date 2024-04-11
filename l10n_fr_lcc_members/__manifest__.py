{
    "name": "l10n_fr_lcc_members",
    "summary": """
        French default params for lcc
        """,
    "author": "Lokavaluto",
    "website": "https://lokavaluto.fr",
    "category": "Accounting",
    "version": "16.0.1.0.0",
    # any module necessary for this one to work correctly
    "depends": ["base", "account"],
    # always loaded
    "data": [
        "views/account_journal.xml",
        "report/invoice_report_templates.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
}
