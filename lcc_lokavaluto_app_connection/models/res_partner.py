from odoo import models, fields, api

class ResPartner(models.Model):
    """ Inherits partner and adds Tasks information in the partner form """
    _inherit = 'res.partner'

    in_mobile_app = fields.Boolean('In the mobile map')
    
    def _get_mobile_app_pro_domain(self, **kwargs):
        return [('in_mobile_app','=',True),
                ('company_type','=', 'company'),
                ("partner_longitude">kwargs.get("minLon") and "partner_longitude"<kwargs.get("maxLon")),
                ("partner_latitude">kwargs.get("minLat") and "partner_latitude"<kwargs.get("maxLat"))]

    def _get_mobile_app_contact_domain(self):
        return [('in_mobile_app','=',True)]