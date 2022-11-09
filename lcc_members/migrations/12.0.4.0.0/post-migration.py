# Copyright 2022 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

@openupgrade.migrate()
def migrate(env, version):
    # with the migration to 12.0.4.0.0, the partner_profiles data are changed (transfered in add-on partner_profiles), 
    # then we have to replace the old one by the new one.
    new_main_profile = env.ref("partner_profiles.partner_profile_main")
    new_public_profile = env.ref("partner_profiles.partner_profile_public")
    new_position_profile = env.ref("partner_profiles.partner_profile_position")
    count = 0
    partners = env["res.partner"].search([])
    for partner in partners:
        if partner.is_main_profile:
            partner.partner_profile = new_main_profile
        elif partner.is_public_profile:
            partner.partner_profile = new_public_profile
        elif partner.is_position_profile:
            partner.partner_profile = new_position_profile
        count += 1
        _logger.info("# %s - %s [%s]" % (count, partner.name, partner.id) )

    
    # the change of partner_profile breaks the links between main and public partners, then we rebuild it.
    _logger.info("Migration: compute public profiles")
    for partner in partners:
        if partner.is_main_profile:
            partner._compute_public_profile_id()

    _logger.info("MIGRATION ENDED WITH SUCCESS")
