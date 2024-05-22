# Copyright 2022 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    _logger.info("MIGRATION 12.0.3.0.0: post-migration scripts START.")

    # Select invoices for which we have to create a credit.request
    env.cr.execute(
        """
        SELECT id, partner_id, temporary_cyclos_amount_credited
        FROM account_invoice
        WHERE temporary_cyclos_amount_credited != 0
    """
    )
    invoices_data = env.cr.fetchall()
    for invoice in invoices_data:
        partner_id = env["res.partner"].browse(invoice[1])
        wallet = env["res.partner.backend"].search(
            [("partner_id", "=", partner_id.id), ("type", "=", "cyclos")], limit=1
        )
        if not wallet:
            continue
        values = {
            "amount": invoice[2],
            "state": "done",
            "partner_id": partner_id.id,
            "wallet_id": wallet.id,
            "invoice_id": invoice[0],
            "no_order": True,
        }
        env["credit.request"].create(values)

    # Drop temporary columns
    env.cr.execute(
        "ALTER TABLE account_invoice DROP COLUMN temporary_cyclos_amount_credited"
    )

    _logger.info("MIGRATION 12.0.3.0.0: post-migration scripts END.")
