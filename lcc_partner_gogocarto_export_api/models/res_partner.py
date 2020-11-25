from odoo import models, fields, api
from ast import literal_eval


class ResPartner(models.Model):
    """ Inherits partner and adds Tasks information in the partner form """
    _inherit = 'res.partner'
    
    def _get_gogocarto_domain(self):
        return [('in_gogocarto','=',True),('is_company','=', True)
                ,('membership_state','in',['paid', 'free'])
                ,('partner_longitude', '!=', float())
                ,('partner_latitude', '!=', float())
                ]

    def _get_team_id_label(self):
        if self.team_id:
            return self.team_id.name
        else:
            return ''

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

    #region Public method for JSON Serialization
    def add_fields(self, element, export_fields):
        for field in export_fields:
            if field.name == "team_id":
                self.__add_computed_node(element, "team_id", self._get_team_id_label)
            elif field.name == "itinerant":
                self.__add_computed_node(element,"itinerant", self._get_itinerant_label)
            elif field.name == "currency_exchange_office":
                self.__add_computed_node(element,"exchange_counter", self._get_exchange_counter_label)
            elif field.name == "team_id":
                self.__add_computed_node(element, "local_group", self._get_team_id_label)
            elif field.name == "industry_id":
                self.__add_computed_node(element, "industry_id", self._get_industry_id_label)
            else:
                self.__add_simple_node(element, field.name)
        return element
    #endregion