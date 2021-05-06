from odoo import models, fields

import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """ Inherits partner and adds Tasks information in the partner form """
    _inherit = 'res.partner'

    in_mobile_app = fields.Boolean('In the mobile map', default=True)

    app_exported_fields = []

    def _get_mobile_app_pro_domain(self, **kwargs):
        return [('in_mobile_app', '=', True),
                ('is_company', '=', True),
                ('partner_longitude', '!=', float()),
                ('partner_latitude', '!=', float()),
                ('partner_longitude', '>', kwargs.get("minLon")),
                ('partner_longitude', '<', kwargs.get("maxLon")),
                ('partner_latitude', '>', kwargs.get("minLat")),
                ('partner_latitude', '<', kwargs.get("maxLat"))]

    # def _get_zipCityName(self):
    #     zipCityName = ''
    #     if self.zip:
    #         zipCityName = self.zip
    #     if self.city:
    #         zipCityName += self.city
    #     return zipCityName

    # def _get_autocompleteLabel(self):
    #     autoCompleteLabel = ""
    #     if self.name:
    #         autoCompleteLabel += self.name
    #     if self._get_zipCityName != '':
    #         autoCompleteLabel += '[' + self._get_zipCityName() + ']'
    #     if self.email:
    #         autoCompleteLabel += '(' + self.email + ')'
    #     return autoCompleteLabel

    # def _is_partner_adherent(self):
    #     if self.membership_state in ('paid', 'free'):
    #         return True
    #     else:
    #         return False

    def in_mobile_app_button(self):
        """ Inverse the value of the field ``in_mobile_app``
            for the current instance. """
        self.in_mobile_app = not self.in_mobile_app

    # def app_serialization(self):
    #     element = {}
    #     self.__add_app_simple_node(element, "id")
    #     self.__add_app_simple_node(element, "name")
    #     self.__add_app_computed_node(element,
    #                                  "autoCompleteLabel",
    #                                  self._get_autocompleteLabel)
    #     self.__add_app_computed_node(element,
    #                                  "adherent",
    #                                  self._is_partner_adherent)
    #     # self.__add_computed_node(element,"image", self.__getImage)
    #     # TODO : mainICC
    #     # TODO : keywords
    #     self.__add_app_simple_node(element, "email")
    #     self.__add_app_simple_node(element, "website")
    #     self.__add_app_simple_node(element, "website_description")
    #     self.__add_app_simple_node(element, "website_short_description")
    #     self.__add_app_nested_node(element, "address",
    #                                "street",
    #                                "street2",
    #                                "zip",
    #                                "city")
    #     self.__add_app_nested_node(element, "coords",
    #                                "partner_latitude",
    #                                "partner_longitude")
    #     self.__add_app_nested_node(element, "phones", "phone", "mobile")
    #     return element

    # def __add_app_simple_node(self, element, fieldName):
    #     if fieldName not in self.app_exported_fields:
    #         self.app_exported_fields.append(fieldName)
    #     if getattr(self, fieldName):
    #         element[fieldName] = self[fieldName]

    # def __add_app_computed_node(self, element, fieldLabel, specificMethod):
    #     if fieldLabel not in self.app_exported_fields:
    #         self.app_exported_fields.append(fieldLabel)
    #     element[fieldLabel] = specificMethod()

    # def __add_app_nested_node(self, element, nestedName, *args):
    #     nest = {}
    #     for arg in args:
    #         self.__add_app_simple_node(nest, arg)
    #     element[nestedName] = nest

    # def debug_app_field_exported(self):
    #     _logger.debug("List of field exported for app mobile:")
    #     for fieldName in self.app_exported_fields:
    #         _logger.debug(fieldName)
