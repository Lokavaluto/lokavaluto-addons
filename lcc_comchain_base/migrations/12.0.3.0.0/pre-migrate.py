# Copyright 2022 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

@openupgrade.migrate()
def migrate(env, version):
    _logger.info("MIGRATION 12.0.3.0.0: pre-migration scripts START.")

    # Add temporary Comchain amount credited column
    env.cr.execute('ALTER TABLE account_invoice ADD temporary_comchain_amount_credited float')
    env.cr.execute('UPDATE account_invoice SET temporary_comchain_amount_credited = comchain_amount_credited')
    # Add temporary amount to credit column
    env.cr.execute('ALTER TABLE account_invoice ADD temporary_comchain_amount_to_credit float')
    env.cr.execute('UPDATE account_invoice SET temporary_comchain_amount_credited = comchain_amount_credited')

    _logger.info("MIGRATION 12.0.3.0.0: pre-migration scripts END.")