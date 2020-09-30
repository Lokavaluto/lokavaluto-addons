from odoo import models, fields, api
from odoo.tools.translate import _

class exchange_counters_config(models.Model):
    _name = 'exchangecounters.config'
    _description = "MLCC Counter Config"
    _inherits = {'pos.config': 'pos_config_id'}

    def _get_group_pos_manager(self):
        return self.env.ref('lcc_exchange_counters.group_exchange_counters_manager')

    def _get_group_pos_user(self):
        return self.env.ref('lcc_exchange_counters.group_exchange_counters_user')