# -*- coding: utf-8 -*-
import logging
from ast import literal_eval
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gogocarto_map_url = fields.Char(readonly=False)
    export_gogocarto_fields = fields.Many2many('ir.model.fields', 'export_field_rel', 'export_id', 'fields_id',
                                               domain="[""('model_id', '=', 'res.partner')\
                                                        ,('name', 'not in', ('name','partner_longitude','partner_latitude'))""]",
                                               readonly=False)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        gogocarto_map_url = ICPSudo.get_param('lcc_partner_gogocartojs.gogocarto_map_url')
        export_gogocarto_fields = ICPSudo.get_param('lcc_partner_gogocartojs.export_gogocarto_fields') if ICPSudo.get_param('lcc_partner_gogocartojs.export_gogocarto_fields') else "[]"  
        res.update(
            gogocarto_map_url=gogocarto_map_url,
            export_gogocarto_fields= [(6, 0, literal_eval(export_gogocarto_fields))]
        )
        return res

    @api.multi
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter']
        ICPSudo.set_param('lcc_partner_gogocartojs.gogocarto_map_url',self.gogocarto_map_url)
        ICPSudo.set_param('lcc_partner_gogocartojs.export_gogocarto_fields',self.export_gogocarto_fields.ids)
        return res




