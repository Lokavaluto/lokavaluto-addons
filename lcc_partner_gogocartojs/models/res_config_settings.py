# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    gogocarto_map_url = fields.Char(readonly=False)
    export_gogocarto_fields = fields.Many2many('ir.model.fields', 
                                               domain="[""('model_id', '=', 'res.partner')""]",
                                               readonly=False)

    @api.model
    def get_values(self):        
        res = super(ResConfigSettings, self).get_values()
        res.update(
            gogocarto_map_url=self.gogocarto_map_url if self.gogocarto_map_url else False,
            export_gogocarto_fields=self.export_gogocarto_fields if self.export_gogocarto_fields else False,
        )
        return res

