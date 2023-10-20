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
        SELECT id, partner_id, temporary_comchain_amount_credited, temporary_comchain_amount_to_credit
        FROM account_invoice
        WHERE temporary_comchain_amount_credited != 0 OR temporary_comchain_amount_to_credit != 0
    """
    )
    invoices_data = env.cr.fetchall()
    for invoice in invoices_data:
        if invoice[2] > 0:
            values = {
                "amount": invoice[2],
                "state": "done",
            }
        elif invoice[3] > 0:
            values = {
                "amount": invoice[3],
                "state": "open",
            }
        else:
            continue
        partner_id = env["res.partner"].browse(invoice[1])
        wallet = env["res.partner.backend"].search(
            [("partner_id", "=", partner_id.id), ("type", "=", "comchain")], limit=1
        )
        if not wallet:
            continue
        values.update(
            {
                "partner_id": partner_id.id,
                "wallet_id": wallet.id,
                "invoice_id": invoice[0],
                "create_order": False,
            }
        )
        env["credit.request"].create(values)

    # Drop temporary columns
    env.cr.execute(
        "ALTER TABLE account_invoice DROP COLUMN temporary_comchain_amount_credited"
    )
    env.cr.execute(
        "ALTER TABLE account_invoice DROP COLUMN temporary_comchain_amount_to_credit"
    )

    _logger.info("MIGRATION 12.0.3.0.0: post-migration scripts END.")
