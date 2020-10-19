from odoo import models, fields, api

class ResPartner(models.Model):
    """ Inherits partner and adds Tasks information in the partner form """
    _inherit = 'res.partner'

    in_gogocarto = fields.Boolean('In gogocarto')
    
    def _get_gogocarto_domain(self):
        return [('in_gogocarto','=',True),('is_company','=', True),('membership_state','in',['paid', 'free'])]


        

    def _get_exchange_counter_label(self):
        if self.currency_exchange_office:
            return 'Exchange counter'
        else:
            return ''

    def _get_itinerant_label(self):
        if self.itinerant:
            return 'Itinerant'
        else:
            return ''