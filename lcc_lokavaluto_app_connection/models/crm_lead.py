from bdb import set_trace
from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools.translate import _


class Lead(models.Model):
    _inherit = "crm.lead"

    refuse_numeric_wallet_creation = fields.Boolean(string=_("Refuse the creation of a numeric wallet."))


    def _get_values_main_partner(self):
        values = super(Lead, self)._get_values_main_partner()
        values["refuse_numeric_wallet_creation"] = self.refuse_numeric_wallet_creation
        return values
