from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)
        

class ResPartner(models.Model):
    """ Inherits partner and adds Tasks information in the partner form """
    _inherit = 'res.partner'

    in_mobile_app = fields.Boolean('In the mobile map', default = True)
    
    def _get_mobile_app_pro_domain(self, **kwargs):
        return [('in_mobile_app','=',True),
                ('is_company','=', True),
                ('partner_longitude', '>', kwargs.get("minLon")),
                ('partner_longitude', '<', kwargs.get("maxLon")),
                ('partner_latitude','>', kwargs.get("minLat")),
                ('partner_latitude', '<', kwargs.get("maxLat"))]

    def _get_zipCityName(self):
        zipCityName =''
        if self.zip:
            zipCityName =self.zip 
        if self.city:
            zipCityName+= self.city
        return zipCityName

    def _get_autocompleteLabel(self):
        autoCompleteLabel = ""
        if self.name:
            autoCompleteLabel+= self.name
        if self._get_zipCityName != '':
            autoCompleteLabel+= '[' + self._get_zipCityName() + ']' 
        if self.email:
            autoCompleteLabel+= '(' + self.email +')'
        return autoCompleteLabel

    def _is_partner_adherent(self):
        if self.membership_state in ('paid', 'free'):
            return True     
        else :
            return False

    def in_mobile_app_button(self):
        """ Inverse the value of the field ``in_mobile_app`` for the current instance. """     
        self.in_mobile_app = not self.in_mobile_app     
       
    
