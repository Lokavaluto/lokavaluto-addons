import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Save Odoo Wallet password for each alt currency
    ## Create tmp column
    cr.execute(
        "ALTER TABLE res_alt_currency ADD tmp_comchain_odoo_wallet_password varchar(255)"
    )

    ## Copy the data
    cr.execute(
        "UPDATE res_alt_currency SET tmp_comchain_odoo_wallet_password = comchain_odoo_wallet_password"
    )
