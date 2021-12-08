# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields
from odoo.tools.translate import _


class PartnerProfile(models.Model):
    _name = "partner.profile"
    _description = "Partner profile to differentiate the attached partner entries"

    name = fields.Char(string=_("Name"), required=True, translate=True, readonly=False)
    ref = fields.Char(string=_("Ref"), required=True, translate=False, readonly=False)

    # TODO: block unlink method.
