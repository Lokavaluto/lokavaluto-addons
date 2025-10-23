import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Save Cyclos currency config
    cr.execute("ALTER TABLE res_company ADD tmp_cyclos_server_url varchar(255)")
    cr.execute("ALTER TABLE res_company ADD tmp_cyclos_server_login varchar(255)")
    cr.execute("ALTER TABLE res_company ADD tmp_cyclos_server_password varchar(255)")
    cr.execute("ALTER TABLE res_company ADD tmp_cyclos_debit_wallet_partner int")
    cr.execute(
        "ALTER TABLE res_company ADD tmp_cyclos_date_last_reconversion_check timestamp"
    )

    ## Copy the data
    cr.execute("UPDATE res_company SET tmp_cyclos_server_url = cyclos_server_url")
    cr.execute("UPDATE res_company SET tmp_cyclos_server_login = cyclos_server_login")
    cr.execute(
        "UPDATE res_company SET tmp_cyclos_server_password = cyclos_server_password"
    )
    cr.execute(
        "UPDATE res_company SET tmp_cyclos_debit_wallet_partner = cyclos_debit_wallet_partner"
    )
    cr.execute(
        "UPDATE res_company SET tmp_cyclos_date_last_reconversion_check = cyclos_date_last_reconversion_check"
    )

    # Identify Cyclos wallets
    cr.execute("ALTER TABLE res_partner_backend ADD tmp_is_cyclos bool")
    cr.execute("UPDATE res_partner_backend SET tmp_is_cyclos=True WHERE type='cyclos'")
