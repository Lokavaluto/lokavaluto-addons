from odoo import models, fields, api
from ast import literal_eval
import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """ Inherits partner and adds Tasks information in the partner form """
    _inherit = 'res.partner'

    in_gogocarto = fields.Boolean('In gogocarto')
    
    def _get_gogocarto_domain(self):
        return [('in_gogocarto','=',True),('is_company','=', True)
                ,('membership_state','in',['paid', 'free'])
                ,('partner_longitude', '!=', float())
                ,('partner_latitude', '!=', float())
                ]

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

    def _get_local_group_label(self):
        if self.team_id:
            return self.team_id.name
        else:
            return ''
    
    def _get_industry_label(self):
        if self.industry_id:
            return self.industry_id.name
        else:
            return ''

    #region Public method for JSON Serialization
    def app_serialization(self):
        element = {}
        element["lon"] = self["partner_longitude"]
        element["lat"] = self["partner_latitude"]
        self.__add_simple_node(element, "name")
        for field in self.__get_export_fields():
            if field.name == "itinerant":
                self.__add_computed_node(element,"itinerant", self._get_itinerant_label)
            elif field.name == "currency_exchange_office":
                self.__add_computed_node(element,"exchange_counter", self._get_exchange_counter_label)
            elif field.name == "team_id":
                self.__add_computed_node(element, "local_group", self._get_local_group_label)
            else:
                self.__add_simple_node(element, field.name)
        
        # self.__add_simple_node(element, "id")
        # self.__add_computed_node(element, "local_group", self._get_local_group_label)
        # self.__add_simple_node(element, "name")
        # self.__add_nested_node(element, "address", "street", "street2","zip", "city")
        # self.__add_nested_node(element, "coords", "partner_latitude", "partner_longitude")
        # self.__add_nested_node(element, "contact_info", "phone", "mobile", "email", "website")
        # self.__add_simple_node(element, "convention_signature_date")
        # self.__add_nested_node(element, "activities", "detailed_activity", "member_comment", "opening_time","legal_activity_code")
        # element["activities"]["main_activity"] = self._get_industry_label()
        # self.__add_computed_node(element,"exchange_counter", self._get_exchange_counter_label)
        # self.__add_computed_node(element,"itinerant", self._get_itinerant_label)
        # self.__add_simple_node(element, "keywords")
        # self.__add_simple_node(element,"reasons_choosing_mlc")
        return element
    #endregion
        
    #region Private method to JSON Serialization
    def __get_export_fields(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        export_field_ids = literal_eval(ICPSudo.get_param('lcc_partner_gogocartojs.export_gogocarto_fields'))
        export_fields = self.env['ir.model.fields'].search([('model_id', '=', 'res.partner'),('id','in', export_field_ids)])
        return export_fields

    def __add_simple_node(self, element, fieldName): 
        if getattr(self, fieldName):
            element[fieldName] = self[fieldName]
    
    def __add_computed_node(self, element, fieldLabel, specificMethod):
        element[fieldLabel] = specificMethod()

    def __add_nested_node(self, element, nestedName, *args):
        nest = {}
        for arg in args:
            self.__add_simple_node(nest, arg)
        element[nestedName] = nest
    #endregion

    #region Public method to debug JSON Serialization
    def debug_field_exported(self):
        _logger.debug("List of field exported:")
        for field in self.__get_export_fields():
            _logger.debug(field.name)
    #endregion