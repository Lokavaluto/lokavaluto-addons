import logging
from odoo.addons.base_rest.components.service import to_bool, to_int
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class PartnerService(Component):
    _inherit = "base.rest.service"
    _name = "partner.service"
    _usage = "partner"
    _collection = "lokavaluto.private.services"
    _description = """
        Partner Services
        Access to the partner services is only allowed to authenticated users.
        If you are not authenticated go to <a href='/web/login'>Login</a>
    """

    def get(self, _id):
        """
        Get partner's informations
        """
        parser = self._get_partner_parser()
        partner = self._get(_id)
        return partner.jsonify(parser)[0]

    def search(self, value, backends_keys=[]):
        """
        Search partner by name, email or phone
        """
        partners = self.env["res.partner"].name_search(value)
        partners = self.env["res.partner"].browse([i[0] for i in partners])
        if not partners:
            partners = self.env["res.partner"].search([('active', '=', True),
                                                        '|', ('email', '=', value),
                                                            '|', ('phone', '=', value),('mobile', '=', value)])    
        return self._get_formatted_partners(partners, backends_keys)


    def favorite(self):
        """
        Get my favorite partner
        """
        partners = self.env["res.partner"].search(
            [('favorite_user_ids', 'in',
              self.env.context.get('uid'))])
        return self._get_formatted_partners(partners, backends_keys)

    def toggle_favorite(self, _id):
        """
        Toggle favorite partner
        """
        partner = self._get(_id)
        parser = self._get_partner_parser()
        partner.write({
           'is_favorite': True,
        })
        return partner.jsonify(parser)[0]

    def _validator_return_toggle_favorite(self):
        res = self._validator_create()
        res.update({"id": {"type": "integer", "required": True, "empty": False}})
        return res

    # pylint:disable=method-required-super
    def create(self, **params):
        """
        Create a new partner
        """
        partner = self.env["res.partner"].create(self._prepare_params(params))
        parser = self._get_partner_parser()
        return partner.jsonify(parser)

    def update(self, _id, **params):
        """
        Update partner informations
        """
        partner = self._get(_id)
        parser = self._get_partner_parser()
        partner.write(self._prepare_params(params))
        return partner.jsonify(parser)

    def archive(self, _id, **params):
        """
        Archive the given partner. This method is an empty method, IOW it
        don't update the partner. This method is part of the demo data to
        illustrate that historically it's not mandatory to defined a schema
        describing the content of the response returned by a method.
        This kind of definition is DEPRECATED and will no more supported in
        the future.
        :param _id:
        :param params:
        :return:
        """
        return {"response": "Method archive called with id %s" % _id}

    # The following method are 'private' and should be never never NEVER call
    # from the controller.

    def _get(self, _id):
        return self.env["res.partner"].browse(_id)

    def _get_formatted_partners(self, partners, backends_keys):
        rows = []
        res = {"count": len(partners), "rows": rows}
        parser = self._get_partner_parser()
        rows = partners.jsonify(parser)
        if backends_keys:
            for row in rows:
                partner_id = row["id"]
                partner = self.env["res.partner"].search([('id', '=', partner_id)])
                credentials = partner._update_search_data(backends_keys)
                row["monujo_backends"] = credentials
        res = {"count": len(partners), "rows": rows}
        return res

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

    def _validator_return_partners(self):
        return {
            "count": {"type": "integer", "required": True},
            "rows": {
                "type": "list",
                "required": True,
                "schema": {"type": "dict", "schema": self._validator_return_get()},
            },
        } 

    def _validator_search(self):
        return {"value": {"type": "string", "nullable": False, "required": True},
                "backends_keys": {
                    "type": "list",
                    "nullable": True,
                    "required": False,
                    "empty": True,
                    "schema": {"type": "string"} #, "nullable": False, "required": False}
                }
        }

    def _validator_return_search(self):
        return self._validator_return_partners()

    def _validator_return_favorite(self):
        return self._validator_return_partners()

    def _validator_create(self):
        res = {
            "name": {"type": "string", "required": True, "empty": False},
            "street": {"type": "string", "nullable": True, "empty": True},
            "street2": {"type": "string", "nullable": True},
            "zip": {"type": "string", "nullable": True, "empty": True},
            "city": {"type": "string", "nullable": True, "empty": True},
            "phone": {"type": "string", "nullable": True, "empty": True},
            "mobile": {"type": "string", "nullable": True, "empty": True},
            "email": {"type": "string", "nullable": True, "empty": True},
            "state": {
                "type": "dict",
                "schema": {
                    "id": {"type": "integer", "coerce": to_int, "nullable": True},
                    "name": {"type": "string"},
                },
            },
            "country": {
                "type": "dict",
                "schema": {
                    "id": {
                        "type": "integer",
                        "coerce": to_int,
                        "required": True,
                        "nullable": False,
                    },
                    "name": {"type": "string"},
                },
            },
            "is_company": {"coerce": to_bool, "type": "boolean"},
            "is_favorite": {"coerce": to_bool, "type": "boolean"},
            "monujo_backends": {"type": "list"},
        }
        return res

    def _validator_return_create(self):
        return self._validator_return_get()

    def _validator_update(self):
        res = self._validator_create()
        for key in res:
            if "required" in res[key]:
                del res[key]["required"]
        return res

    def _validator_return_update(self):
        return self._validator_return_get()

    def _validator_archive(self):
        return {}

    def _get_partner_parser(self):
        parser = [
            'id',
            'name',
            'street',
            'street2',
            'zip',
            'city',
            'mobile',
            'email',
            'phone',
            'is_favorite',
            'is_company',
            ('country_id', ['id', 'name']),
            #('state', ['id','name'])
        ]
        return parser
