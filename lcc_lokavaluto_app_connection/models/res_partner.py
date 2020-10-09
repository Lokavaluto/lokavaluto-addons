from odoo import models, fields, api

class ResPartner(models.Model):
    """ Inherits partner and adds Tasks information in the partner form """
    _inherit = 'res.partner'

    in_mobile_app = fields.Boolean('In the mobile map')
    
    _get_mobile_app_pro_domain(self)
        return [('in_mobile_app','=',True),('company_type','=', 'company')]

    _get_mobile_app_contact_domain(self)
        return [('in_mobile_app','=',True))]