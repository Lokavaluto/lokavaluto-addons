import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    cr.execute("""
        SELECT
            odoo_wallet_partner_id,
            tmp_comchain_odoo_wallet_password
        FROM res_alt_currency
        WHERE active=True AND engine='comchain'
    """)

    # Write Odoo Wallet password in the matching res_partner_backend
    for (
            odoo_wallet_partner_id,
            tmp_comchain_odoo_wallet_password,
    ) in cr.fetchall():
        if not tmp_comchain_odoo_wallet_password:
            continue

        odoo_wallet_id = env["res.partner"].browse(odoo_wallet_partner_id).lcc_backend_ids[0].id
        cr.execute(
            f"UPDATE res_partner_backend\
            SET comchain_wallet_pwd='{tmp_comchain_odoo_wallet_password}'\
            WHERE id={odoo_wallet_id}")

    # Clean res_alt_currency table
    cr.execute("ALTER TABLE res_alt_currency DROP COLUMN tmp_comchain_odoo_wallet_password")
