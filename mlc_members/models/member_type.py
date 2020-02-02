# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields
from odoo.tools.translate import _


class member_type(models.Model):
    _name = "member_type"

    name = fields.Char(
        string=_("Name"),
        required=False,
        translate=False,
        readonly=False
    )
