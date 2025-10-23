import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Save Comchain currency config
    ## Create tmp columns
    cr.execute("ALTER TABLE res_company ADD tmp_comchain_currency_name varchar(255)")
    cr.execute("ALTER TABLE res_company ADD tmp_safe_wallet_partner_id int")
    cr.execute("ALTER TABLE res_company ADD tmp_odoo_wallet_partner_id int")
    cr.execute(
        "ALTER TABLE res_company ADD tmp_comchain_odoo_wallet_password varchar(255)"
    )
    cr.execute("ALTER TABLE res_company ADD tmp_message_from varchar(255)")
    cr.execute("ALTER TABLE res_company ADD tmp_message_to varchar(255)")
    cr.execute("ALTER TABLE res_company ADD tmp_last_block_checked_nb int")

    ## Copy the data
    cr.execute(
        "UPDATE res_company SET tmp_comchain_currency_name = comchain_currency_name"
    )
    cr.execute(
        "UPDATE res_company SET tmp_safe_wallet_partner_id = safe_wallet_partner_id"
    )
    cr.execute(
        "UPDATE res_company SET tmp_odoo_wallet_partner_id = odoo_wallet_partner_id"
    )
    cr.execute(
        "UPDATE res_company SET tmp_comchain_odoo_wallet_password = comchain_odoo_wallet_password"
    )
    cr.execute("UPDATE res_company SET tmp_message_from = message_from")
    cr.execute("UPDATE res_company SET tmp_message_to = message_to")
    cr.execute(
        "UPDATE res_company SET tmp_last_block_checked_nb = last_block_checked_nb"
    )

    # Identify Comchain wallets
    cr.execute("ALTER TABLE res_partner_backend ADD tmp_is_comchain bool")
    cr.execute(
        "UPDATE res_partner_backend SET tmp_is_comchain=True WHERE type='comchain'"
    )
