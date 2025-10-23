import logging

# from odoo.upgrade import util
from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    cr.execute("""
        SELECT
            tmp_activate_automatic_topup,
            tmp_commission_product_id,
            tmp_cyclos_server_url,
            tmp_cyclos_server_login,
            tmp_cyclos_server_password,
            tmp_cyclos_debit_wallet_partner,
            tmp_cyclos_date_last_reconversion_check
        FROM res_company
        WHERE active=True
    """)

    for (
        tmp_activate_automatic_topup,
        tmp_commission_product_id,
        tmp_cyclos_server_url,
        tmp_cyclos_server_login,
        tmp_cyclos_server_password,
        tmp_cyclos_debit_wallet_partner,
        tmp_cyclos_date_last_reconversion_check,
    ) in cr.fetchall():
        # Create Cyclos res.alt.currency
        if not tmp_cyclos_server_url:
            continue

        data = {
            "name": tmp_cyclos_server_url,
            "ident": tmp_cyclos_server_url,
            "engine": "cyclos",
            "activate_automatic_topup": tmp_activate_automatic_topup,
            "currency_unit_product_id": env.ref(
                "lcc_cyclos_base.product_product_cyclos"
            ).id,
            "commission_product_id": tmp_commission_product_id,
            "cyclos_server_url": tmp_cyclos_server_url,
            "cyclos_server_login": tmp_cyclos_server_login,
            "cyclos_server_password": tmp_cyclos_server_password,
            "cyclos_debit_wallet_partner": tmp_cyclos_debit_wallet_partner,
            "cyclos_date_last_reconversion_check": tmp_cyclos_date_last_reconversion_check,
        }
        cyclos_currency = env["res.alt.currency"].create(data)

    # Clean res_company table
    cr.execute("ALTER TABLE res_company DROP COLUMN tmp_cyclos_server_url")
    cr.execute("ALTER TABLE res_company DROP COLUMN tmp_cyclos_server_login")
    cr.execute("ALTER TABLE res_company DROP COLUMN tmp_cyclos_server_password")
    cr.execute("ALTER TABLE res_company DROP COLUMN tmp_cyclos_debit_wallet_partner")
    cr.execute(
        "ALTER TABLE res_company DROP COLUMN tmp_cyclos_date_last_reconversion_check"
    )

    # Fill the ident field of Cyclos wallets
    nb = 0
    cr.execute("SELECT id FROM res_partner_backend WHERE tmp_is_cyclos = True")
    for id in cr.fetchall():
        wallet = env["res.partner.backend"].browse(id)
        data = {"alt_currency_id": cyclos_currency.id, "ident": wallet.cyclos_id}
        wallet.write(data)
        nb += 1

    _logger.info(f"Ident field filled for {nb} Cyclos wallets")

    cr.execute("ALTER TABLE res_partner_backend DROP COLUMN tmp_is_cyclos")
