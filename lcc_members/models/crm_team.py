from odoo import fields, models
from odoo.tools.translate import _


class Team(models.Model):
    _inherit = "crm.team"

    local_group = fields.Boolean(string=_("Is a local group"))
