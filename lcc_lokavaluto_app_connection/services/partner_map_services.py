import logging
from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.base_rest.components.service import to_bool, to_int
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class PartnerMapService(Component):
    _inherit = "base.rest.service"
    _name = "partner_map.service"
    _usage = "partner_map"
    _collection = "lokavaluto.public.services"
    _description = """
        Partner Map Services
        Access to the ping services is allowed to everyone
    """

    ##########################################################
    # TO CLEAN LATER
    ##########################################################
    def search_in_area(self, bounding_box, categories):
        """
        Searh partner in a area defined by latitude and longitude
        """
        all_partner = self.env['res.partner'].sudo()
        partners = all_partner.search(all_partner._get_mobile_app_pro_domain(bounding_box, categories))
        rows = []
        res = {"count": len(partners), "rows": rows}
        parser = self._get_partner_parser()
        rows = partners.jsonify(parser)
        _logger.debug('#################### rows: %s' % rows)
        res = {"count": len(partners), "rows": rows}
        return res
    ##########################################################
    ##########################################################

    @restapi.method(
        [(["/search"], "GET")],
        input_param=Datamodel("partners.map.search.param"),
    )
    def search(self, partners_map_search_param):
        """
        Searh partner in a area defined by latitude and longitude
        """
        _logger.debug('#### PARAM SEARCH : %s' % partners_map_search_param)
        bounding_box = partners_map_search_param.bounding_box
        categories = partners_map_search_param.categories
        all_partner = self.env['res.partner'].sudo()
        partners = all_partner.search(all_partner._get_mobile_app_pro_domain(bounding_box, categories))
        rows = []
        res = {"count": len(partners), "rows": rows}
        parser = self._get_partner_parser()
        rows = partners.jsonify(parser)
        _logger.debug('#################### rows: %s' % rows)
        res = {"count": len(partners), "rows": rows}
        return res

    

    # The following method are 'private' and should be never never NEVER call
    # from the controller.

    # Validator

    ##########################################################
    # TO CLEAN LATER
    ##########################################################
    def _validator_search_in_area(self):
        return {"bounding_box": {
                    "type": "dict",
                    "schema": {
                        "minLat": {"type": "string", "required": True},
                        "maxLat": {"type": "string", "required": True},
                        "minLon": {"type": "string", "required": True},
                        "maxLon": {"type": "string", "required": True},
                    },
                    "required": True
                },
                "categories" : {
                    "type": "list", 
                    "schema": {"type": "string"},
                    "required": False,
                    "nullable": True
                },
               }
    ##########################################################
    ##########################################################


    def _validator_return_search_in_area(self):
        res = {
            "count": {"type": "integer", "required": True},
            "rows": {
                "type": "list",
                "required": True,
                "schema": {"type": "dict", "schema": self._return_partner_in_area()},
            },
        }
        return res

    def _return_partner_in_area(self):
        res = {
            "id": {"type": "integer", "required": True, "nullable": False},
            "name": {"type": "string", "required": True, "empty": True},
            "partner_latitude": {"type": "float", "required": True, "empty": True},
            "partner_longitude": {"type": "float", "required": True, "empty": True},
            "industry_id": {
                "type": "dict",
                "schema": {
                    "id": {
                        "type": "integer",
                        "coerce": to_int,
                        "nullable": False,
                        "empty": True
                    },
                    "name": {"type": "string", "empty": True},
                },
                "empty": True,
                "required": False,
                "nullable": True,
            },
            "opening_time": {"type": "string", "required": False, "empty": True, "nullable": True},
        }
        return res

    def _get_partner_parser(self):
        parser = [
            'id',
            'name',
            'partner_latitude',
            'partner_longitude',
            ('industry_id', ['id', 'name']),
            'opening_time',
        ]
        return parser
