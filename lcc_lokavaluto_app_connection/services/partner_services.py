import logging
from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.base_rest.components.service import to_bool, to_int
from odoo.addons.component.core import Component
from odoo.http import request
from odoo.exceptions import (
    AccessDenied,
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)

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

    def backend_credentials(self):
        """
        This method is used to authenticate and get the token for the user on mobile app.
        """
        partner = self.env.user.partner_id
        response = partner._get_backend_credentials()
        return response

    @restapi.method(
        [(["/<int:id>/get", "/<int:id>"], "GET")],
        input_param=Datamodel("partner.info.get.param")
    )
    def get(self, _id, partner_info_get_param):
        """
        Get partner's informations. If id == 0 return 'me'
        """
        website_url = partner_info_get_param.website_url
        domain = [('active', '=', True)]
        if _id is None:
            _id = 0
        if _id == 0:
            _id = self.env.user.partner_id.id
        domain.extend([('id', '=', _id)])
        if website_url:
            partner_id = website_url.split('-')[-1]
            try:
                partner_id = int(partner_id)
                domain.extend([('id', '=', partner_id)])
            except ValueError:
                raise MissingError('Url not valid.')
        partners = self.env["res.partner"].search(domain)

        if len(partners) == 1:
            parser = self._get_partner_parser()
            res = partners.jsonify(parser)[0]
            backend_keys = partner_info_get_param.backend_keys
            if backend_keys:
                res["monujo_backends"] = list(partners)[0]._update_search_data(backend_keys)
            return res
        else:
            raise MissingError("No partner found - please check your request")

    ##########################################################
    # TO CLEAN LATER
    ##########################################################
    def partner_search(self, **params):
        """
        Search partner by name, email or phone
        """
        value = params.get('value', False)
        backend_keys = params.get('backend_keys', [])
        partners = self.env["res.partner"].name_search(value)
        partners = self.env["res.partner"].browse([i[0] for i in partners])
        if not partners:
            partners = self.env["res.partner"].search([('active', '=', True),
                                                        '|', ('email', '=', value),
                                                        '|', ('phone', '=', value),('mobile', '=', value)])   
        partners = partners - self.env.user.partner_id        
        if backend_keys:
            partners = partners.filtered(lambda r : r.backends() & set(backend_keys))        
        return self._get_formatted_partners(partners, backend_keys)
    ##########################################################
    ##########################################################


    @restapi.method(
        [(["/partner_search", "/search"], "GET")],
        input_param=Datamodel("partner.search.info"),
    )
    def get_partner_search(self, partner_search_info):
        """
        Search partner by name, email or phone
        is_favorite: if True return only favorite partner, else all
        is_company: if True search in company else in personal partner
        website_url: we can search we url of the web site if needed
        note: 
           - when search personal partner we need complete et exact match with value.
           - personl partner only search on mobile, phone and email
        """
        _logger.debug('PARAMS: %s' % partner_search_info)
        value = partner_search_info.value
        backend_keys = partner_search_info.backend_keys
        is_favorite = partner_search_info.is_favorite
        is_company = partner_search_info.is_company
        domain = [('id', '!=', self.env.user.partner_id.id),('active', '=', True)]
        offset = partner_search_info.offset if partner_search_info.offset else 0
        limit = partner_search_info.limit if partner_search_info.limit else 0
        website_url = partner_search_info.website_url
        order = partner_search_info.order
        if is_favorite or not value:
            domain.extend([('favorite_user_ids', 'in', self.env.uid)])
        domain.extend([('is_company', '=', 1 if is_company else 0)])
        if value:
            if is_company:
                domain.extend(['|','|', '|', ('display_name', 'ilike', value),
                               ('email', 'ilike', value),
                               ('phone', 'ilike', value),
                               ('mobile', 'ilike', value)])
            else:
                domain.extend(['|', '|', ('email', '=', value),
                                         ('phone', '=', value),
                                         ('mobile', '=', value)])
        if website_url:
            partner_id = website_url.split('-')[-1]
            try:
                partner_id = int(partner_id)
                domain.extend([('id', '=', partner_id)])
            except ValueError:
                raise MissingError('Url not valid.')
        _logger.debug("DOMAIN: %s" % domain)
        partners = self.env["res.partner"].search(domain, limit=limit, offset=offset, order=order)
        _logger.debug("partners: %s" % partners)
        if backend_keys:
            partners = partners.filtered(lambda r : r.backends() & set(backend_keys))        
        return self._get_formatted_partners(partners, backend_keys)


    @restapi.method(
        [(["/accounts", ], "GET")],
        input_param=Datamodel("account.search.info"),
    )
    def search_accounts(self, account_search_info):
        _logger.debug('PARAMS: %s' % account_search_info)
        backend_keys = account_search_info.backend_keys
        domain = [
            ('active', '=', True),
        ]
        domain_staging = []

        domains_unvalidated = self.env["res.partner"].domains_is_unvalidated_currency_backend()
        for backend_id, d in domains_unvalidated.items():
            domain_staging = ['|'] + d + domain_staging if domain_staging else d

        domain += domain_staging

        offset = account_search_info.offset if account_search_info.offset else 0
        limit = account_search_info.limit if account_search_info.limit else 0
        order = account_search_info.order
        _logger.debug("DOMAIN: %s" % domain)
        partners = self.env["res.partner"].search(domain, limit=limit, offset=offset, order=order)
        _logger.debug("partners: %s" % partners)
        if backend_keys: ## filter out partners not having the queried backends
            partners = partners.filtered(lambda r: r.backends() & set(backend_keys))

        ## Format output
        rows = []
        res = {"count": len(partners), "rows": rows}
        parser = self._get_partner_parser()
        rows = partners.jsonify(parser)
        if backend_keys:
            for row in rows:
                partner_id = row["id"]
                row["monujo_backends"] = {}
                for backend_key in backend_keys:
                    partner = self.env["res.partner"].search(
                        [('id', '=', partner_id)] + domains_unvalidated[backend_key])
                    if len(partner) == 0:
                        continue
                    row["monujo_backends"].update(
                        partner._update_search_data([backend_key])
                    )

        res = {"count": len(partners), "rows": rows}
        return res

        return self._get_formatted_partners(partners, backend_keys)


    ##########################################################
    # TO CLEAN LATER
    ##########################################################
    @restapi.method(
        [(["/get_by_url"], "GET")],
        input_param=Datamodel("partner.url.get.info"),
    )
    def get_by_url(self, partner_url_get_info):
        """
        Get a partner with a website_url "/partners/..."
        """
        _logger.debug('PARAMS: %s' % partner_url_get_info)
        url = partner_url_get_info.url
        partners = self.env["res.partner"].search([('active', '=', True)])
        partners = partners.filtered(lambda r : r.website_url == url)

        if len(partners) > 0:
            parser = self._get_partner_parser()
            res = partners.jsonify(parser)[0]
            backend_keys = partner_url_get_info.backend_keys
            if backend_keys:
                res["monujo_backends"] = list(partners)[0]._update_search_data(backend_keys)
            return res
        else:
            raise MissingError("No partner found - please check your url")
    ##########################################################
    ##########################################################

    @restapi.method(
        [(["/<int:id>/favorite/set"], "PUT")],
    )
    def set_favorite(self, _id):
        """
        Set partner as favorite
        """
        partner = self._get(_id)
        partner.write({
            'is_favorite': True,
        })
        return {}

    @restapi.method(
        [(["/<int:id>/favorite/unset"], "PUT")],
    )
    def unset_favorite(self, _id):
        """
        Unset partner as favorite
        """
        partner = self._get(_id)
        partner.write({
            'is_favorite': False,
        })
        return {}

    @restapi.method(
        [(["/<int:id>/favorite/toggle"], "PUT")],
    )
    def new_toggle_favorite(self, _id):
        """
        Toggle partner as favorite/not favorite
        """
        partner = self._get(_id)
        if partner.is_favorite:
            return self.unset_favorite(_id)
        else:
            return self.set_favorite(_id)


    ##########################################################
    # TO CLEAN LATER
    ##########################################################
    def favorite(self):
        """
        Get my favorite partner
        """
        partners = self.env["res.partner"].search(
            [('favorite_user_ids', 'in',
              self.env.context.get('uid'))])
        return self._get_formatted_partners(partners, [])

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
    ##########################################################
    ##########################################################

    ##########################################################
    # Private methods
    ##########################################################
    # The following method are 'private' and should be never never NEVER call
    # from the controller.

    def _get(self, _id):
        return self.env["res.partner"].browse(_id)

    def _get_formatted_partners(self, partners, backend_keys):
        rows = []
        res = {"count": len(partners), "rows": rows}
        parser = self._get_partner_parser()
        rows = partners.jsonify(parser)
        if backend_keys:
            for row in rows:
                partner_id = row["id"]
                partner = self.env["res.partner"].search([('id', '=', partner_id)])
                credentials = partner._update_search_data(backend_keys)
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
            'qr_url',
            'qr_content',
            #('state', ['id','name'])
        ]
        return parser

    ##########################################################
    # Request Validators
    ##########################################################
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
            "qr_url": {"type": "string", "nullable": True, "empty": True},
            "qr_content": {"type": "string", "nullable": True, "empty": True},
            "monujo_backends": {"type": "dict"},
        }
        return res

    def _validator_update(self):
        res = self._validator_create()
        for key in res:
            if "required" in res[key]:
                del res[key]["required"]
        return res

    def _validator_search(self):
        return {"value": {"type": "string", "nullable": False, "required": True},
                "backend_keys": {
                    "type": "list",
                    "nullable": True,
                    "required": False,
                    "empty": True,
                    "schema": {"type": "string"} #, "nullable": False, "required": False}
                }
        }

    ##########################################################
    # TO CLEAN LATER
    ##########################################################
    def _validator_partner_search(self):
        return {"value": {"type": "string", "nullable": False, "required": True},
                "backend_keys": {
                    "type": "list",
                    "nullable": True,
                    "required": False,
                    "empty": True,
                    "schema": {"type": "string"} #, "nullable": False, "required": False}
                }
        }
    ##########################################################
    ##########################################################

    def _validator_return_create(self):
        return self._validator_return_get()

    def _validator_return_update(self):
        return self._validator_return_get()

    def _validator_return_search(self):
        return self._validator_return_partners()

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

    def _validator_return_favorite(self):
        return self._validator_return_partners()

    def _validator_return_toggle_favorite(self):
        res = self._validator_create()
        res.update({"id": {"type": "integer", "required": True, "empty": False}})
        return res
