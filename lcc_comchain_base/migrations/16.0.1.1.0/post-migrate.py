import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    cr.execute("""
        SELECT
            tmp_comchain_currency_name,
            tmp_activate_automatic_topup,
            tmp_commission_product_id,
            tmp_safe_wallet_partner_id,
            tmp_odoo_wallet_partner_id,
            tmp_comchain_odoo_wallet_password,
            tmp_message_from,
            tmp_message_to,
            tmp_last_block_checked_nb
        FROM res_company
        WHERE active=True
    """)

    # Create Comchain res.alt.currency
    for (
        tmp_comchain_currency_name,
        tmp_activate_automatic_topup,
        tmp_commission_product_id,
        tmp_safe_wallet_partner_id,
        tmp_odoo_wallet_partner_id,
        tmp_comchain_odoo_wallet_password,
        tmp_message_from,
        tmp_message_to,
        tmp_last_block_checked_nb,
    ) in cr.fetchall():
        if not tmp_comchain_currency_name:
            continue

        data = {
            "name": tmp_comchain_currency_name,
            "ident": tmp_comchain_currency_name,
            "engine": "comchain",
            "activate_automatic_topup": tmp_activate_automatic_topup,
            "currency_unit_product_id": env.ref(
                "lcc_comchain_base.product_product_comchain"
            ).id,
            "commission_product_id": tmp_commission_product_id,
            "safe_wallet_partner_id": tmp_safe_wallet_partner_id,
            "odoo_wallet_partner_id": tmp_odoo_wallet_partner_id,
            "comchain_odoo_wallet_password": tmp_comchain_odoo_wallet_password,
            "message_from": tmp_message_from,
            "message_to": tmp_message_to,
            "last_block_checked_nb": tmp_last_block_checked_nb,
        }
        comchain_currency = env["res.alt.currency"].create(data)

    # Clean res_company table
    cr.execute("ALTER TABLE res_company DROP COLUMN tmp_comchain_currency_name")
    cr.execute("ALTER TABLE res_company DROP COLUMN tmp_safe_wallet_partner_id")
    cr.execute("ALTER TABLE res_company DROP COLUMN tmp_odoo_wallet_partner_id")
    cr.execute("ALTER TABLE res_company DROP COLUMN tmp_comchain_odoo_wallet_password")
    cr.execute("ALTER TABLE res_company DROP COLUMN tmp_message_from")
    cr.execute("ALTER TABLE res_company DROP COLUMN tmp_message_to")
    cr.execute("ALTER TABLE res_company DROP COLUMN tmp_last_block_checked_nb")

    # Fill the ident field of Comchain wallets
    nb = 0
    cr.execute("SELECT id FROM res_partner_backend WHERE tmp_is_comchain = True")
    for id in cr.fetchall():
        wallet = env["res.partner.backend"].browse(id)
        data = {"alt_currency_id": comchain_currency.id, "ident": wallet.comchain_id}
        wallet.write(data)
        nb += 1

    _logger.info(f"Ident field filled for {nb} Comchain wallets")

    cr.execute("ALTER TABLE res_partner_backend DROP COLUMN tmp_is_comchain")
