import logging
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

    def search_in_area(self, **params):
        """
        Searh partner in a area defined by latitude and longitude
        """
        partners = _get_mobile_app_pro_domain(params)
        rows = []
        res = {"count": len(partners), "rows": rows}
        parser = self._get_partner_parser()
        rows = partners.jsonify(parser)
        res = {"count": len(partners), "rows": rows}
        _logger.debug('rows: %s' % rows)
        return res

    

    # The following method are 'private' and should be never never NEVER call
    # from the controller.

    def _get(self, _id):
        return self.env["res.partner"].browse(_id)

    def _prepare_params(self, params):
        for key in ["country", "state"]:
            if key in params:
                val = params.pop(key)
                if val.get("id"):
                    params["%s_id" % key] = val["id"]
        return params

    # Validator
    def _validator_return_get(self):
        res = self._validator_create()
        _logger.debug("res: %s" % res)
        res.update({"id": {"type": "integer", "required": True, "empty": False}})

        return res

    def _validator_search(self):
        return {"name": {"type": "string", "nullable": False, "required": True}}

    def _validator_return_search(self):
        return {
            "count": {"type": "integer", "required": True},
            "rows": {
                "type": "list",
                "required": True,
                "schema": {"type": "dict", "schema": self._validator_return_get()},
            },
        }

    def _validator_create(self):
        res = {
            "name": {"type": "string", "required": True, "empty": False},
            "partner_latitude": {"type": "string", "required": True, "empty": False},
            "partner_longiture": {"type": "string", "required": True, "empty": False},
            "industry_id" : {"type": "string", "required": True, "empty": False},
            "opening_time" : {"type": "string", "required": False, "empty": False},
            #"street": {"type": "string", "nullable": True, "empty": True},
            #"street2": {"type": "string", "nullable": True},
            #"zip": {"type": "string", "nullable": True, "empty": True},
            #"city": {"type": "string", "nullable": True, "empty": True},
            #"phone": {"type": "string", "nullable": True, "empty": True},
            #"mobile": {"type": "string", "nullable": True, "empty": True},
            #"email": {"type": "string", "nullable": True, "empty": True},
            #"state": {
            #    "type": "dict",
            #    "schema": {
            #        "id": {"type": "integer", "coerce": to_int, "nullable": True},
            #        "name": {"type": "string"},
            #    },
            #},
            #"country": {
            #    "type": "dict",
            #    "schema": {
            #           "id": {
            #            "type": "integer",
            #            "coerce": to_int,
            #            "required": True,
            #            "nullable": False,
            #        },
            #        "name": {"type": "string"},
            #    },
            #},
            #"is_company": {"coerce": to_bool, "type": "boolean"},
        }
        return res


    def _get_partner_parser(self):
        parser = [
            'id',
            'name',
            'partner_latitude',
            'partner_longiture',
            'industry_id',
            'opening_time'
            #'street',
            #'street2',
            #'zip',
            #'city',
            #'mobile',
            #'email',
            #'phone',
            #('country_id', ['id', 'name']),
            #('state', ['id','name'])
        ]
        return parser
