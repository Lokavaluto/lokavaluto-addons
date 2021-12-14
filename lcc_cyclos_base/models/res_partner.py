import requests
import json
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    ''' Inherits partner, adds Cyclos fields in the partner form, and functions'''
    _inherit = 'res.partner'

    cyclos_create_response = fields.Text(string='Cyclos create response')
    cyclos_active = fields.Boolean(string='Cyclos OK')
    cyclos_id = fields.Char(string="Cyclos id")
    cyclos_status = fields.Char(string="Cyclos Status")

    @api.multi
    def open_commercial_member_entity(self):
        """ Utility method used to add an "Open Company" button in partner views """
        self.ensure_one()
        company_form_id = self.env.ref('lcc_members.main_members_view').id
        return {'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'view_mode': 'form',
                'views': [(company_form_id, 'form')],
                'res_id': self.commercial_partner_id.id,
                'target': 'current',
                'flags': {'form': {'action_buttons': True}}}

    def _cyclos_rest_call(self,
                          method,
                          entrypoint,
                          data={},
                          api_login=False,
                          api_password=False):
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        requests.packages.urllib3.disable_warnings()
        if not api_login:
            api_login = self.env.user.company_id.cyclos_server_login
        if not api_password:
            api_password = self.env.user.company_id.cyclos_server_password
        api_url = '%s%s' % (self.env.user.company_id.cyclos_server_url,
                            entrypoint)
        res = requests.request(method.lower(),
                               api_url,
                               auth=HTTPBasicAuth(api_login, api_password),
                               verify=False,
                               data=json.dumps(data),
                               headers=headers)
        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            _logger.debug(e.response.json())
            if e.response.status_code == 422:
                json_error = e.response.json()
                if json_error.get('code') == 'validation':
                    msg = ["  - %s: %s" % (k, ", ".join(v))
                            for k, v in json_error.get('propertyErrors').items()]
                    raise ValueError("Cyclos serveur complained about:\n%s"
                                        % "\n".join(msg), e.response)
            raise
        return res

    @property
    def _cyclos_backend_id(self):
        parsed_uri = urlparse(self.env.user.company_id.cyclos_server_url)
        if not parsed_uri:  ## is backend available and configured on odoo
            return False
        domain = self.env.user.company_id.cyclos_server_url.split('/')[2]
        return 'cyclos:%s' % domain

    def _cyclos_backend_data(self):
        """Prepare backend data to be sent by credentials requests"""
        backend_id = self._cyclos_backend_id
        if not backend_id:  ## is backend available and configured on odoo
            return []
        data = {
            'type': backend_id,
            'accounts': [],
        }
        if self.cyclos_id:
            data['accounts'].append({
                'owner_id': self.cyclos_id,
                'url': self.env.user.company_id.cyclos_server_url,
                'active': self.cyclos_active,
            })
        return [data]


    def _update_auth_data(self, password):
        self.ensure_one()
        data = super(ResPartner, self)._update_auth_data(password)
        # Update cyclos password with odoo one from authenticate session
        backend_data = self._cyclos_backend_data()
        if backend_data and self.cyclos_active:
            self.forceCyclosPassword(password)
            new_token = self.createCyclosUserToken(self.id, password)
            if new_token:
                for ua in backend_data[0]["accounts"]:
                    ua["token"] = new_token
        data.extend(backend_data)
        return data

    def _get_backend_credentials(self):
        self.ensure_one()
        data = super(ResPartner, self)._get_backend_credentials()
        data.extend(self._cyclos_backend_data())
        return data

    def _update_search_data(self, backend_keys):
        self.ensure_one()
        #_logger.debug('SEARCH: backend_keys = %s' % backend_keys)
        data = super(ResPartner, self)._update_search_data(backend_keys)
        for backend_key in backend_keys:
            if backend_key.startswith("cyclos:") and self.cyclos_id:
                data[backend_key] = [self.cyclos_id]
        #_logger.debug('SEARCH: data %s' % data)
        return data

    def domains_is_unvalidated_currency_backend(self):
        parent_domains = super(ResPartner, self).domains_is_unvalidated_currency_backend()
        parent_domains[self._cyclos_backend_id] = \
            ['&', ('cyclos_active', '=', False), ('cyclos_id', '!=', False)]
        return parent_domains

    def backends(self):
        self.ensure_one()
        backends = super(ResPartner, self).backends()
        if self.cyclos_id:
            cyclos_serveur_url = self.env.user.company_id.cyclos_server_url
            remove = ['https://','http://','/api']
            for value in remove:
                cyclos_serveur_url = cyclos_serveur_url.replace(value, '')
            return backends | {"%s:%s" % ("cyclos", cyclos_serveur_url)}
        else:
            return backends

    @api.multi
    def cyclosCreateOrder(self, owner_id, amount):
        order = self.env['sale.order']
        line = self.env['sale.order.line']
        cyclos_product = self.env.ref('lcc_cyclos_base.product_product_cyclos')
        _logger.debug('PARTNER IN SELF?: %s(%s)' % (self.name, self.id))
        for partner in self:
            # TODO: case with contact of a company ?
            order_vals = {
                'partner_id': partner.id,
                }
            order_vals = order.play_onchanges(order_vals, ['partner_id'])
            _logger.debug("CYCLOS ORDER: %s" % order_vals)
            order_id = order.create(order_vals)
            line_vals = {
                'order_id': order_id.id,
                'product_id': cyclos_product.id,
            }
            line_vals = line.play_onchanges(line_vals, ['product_id'])
            line_vals.update(
                {
                    'product_uom_qty': amount,
                    'price_unit': 1,
                    # TODO: Taxes ?  
                }
            )
            _logger.debug("CYCLOS ORDER LINE: %s" % line_vals)
            line.create(line_vals)
            order_id.write(
                {'state': 'sent',
                 'require_signature': False,
                 'require_payment': True}
            )
        return order_id

    @api.multi
    def action_credit_cyclos_account(self, amount):
        for record in self:
            data = {
                'amount': amount,
                'description': 'Credited by %s' % record.company_id.name,
                'subject': record.cyclos_id if record.cyclos_active else record.parent_id.cyclos_id,
                'type': 'debit.toPro' if record.is_company else 'debit.toUser',
            }
            _logger.debug("data: %s" % data)
            res = record._cyclos_rest_call(
                'POST',
                '/system/payments',
                data=data)
            _logger.debug("res: %s" % res)


    @api.multi
    def addCyclosUser(self):
        for record in self:
            group = 'particuliers' if record.company_type == 'person' else 'professionnels'
            data = {
                'username': record.id,
                'name': record.name,
                'email': record.email,
                'group': group,
                'passwords': [
                    {
                        'type': 'login',
                        'value': 'Odoo1234',
                        'checkConfirmation': True,
                        'confirmationValue': 'Odoo1234',
                        'forceChange': False
                    }
                ],
                'skipActivationEmail': True,
                'addresses': [
                    {
                        'name': record.name,
                        'addressLine1': record.street,
                        'addressLine2': record.street2,
                        'zip': record.zip,
                        'city': record.city,
                        'location': {
                            'latitude': record.partner_latitude,
                            'longitude': record.partner_longitude,
                            },
                        'defaultAddress': True,
                        'hidden': True,
                        'contactInfo': {
                            'email': record.email,
                            'mobilePhone': record.mobile.strip() if record.mobile else '',
                            }
                    }
                ],
            }
            try:
                res = record._cyclos_rest_call('POST', '/users', data=data)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 422:
                    json_error = e.response.json()
                    if json_error.get('code') == 'validation':
                        msg = ["  - %s: %s" % (k, ", ".join(v))
                               for k, v in json_error.get('propertyErrors').items()]
                        raise ValueError("Cyclos serveur complained about:\n%s"
                                         % "\n".join(msg))
                raise

            record.cyclos_create_response = res.text
            data = json.loads(res.text)
            if data:
                _logger.debug("data: %s" % data)
                record.write({
                    'cyclos_id': data.get('user')['id'] if data.get('user', False) else '',
                    'cyclos_status': data.get('status', ''),
                })
            if record.company_type == 'person':
                res = record.validateCyclosUser()

    @api.multi
    def validateCyclosUser(self):
        for record in self:
            res = record._cyclos_rest_call(
                'POST',
                '/%s/registration/validate' % record.cyclos_id)
            _logger.debug("res: %s" % res.text)
            record.cyclos_create_response = res.text
            data = json.loads(res.text)
            if data.get('status', False) and data.get('status') == "active":
                record.write({
                    'cyclos_active': True,
                    'cyclos_status': data.get('status', ''),
                })

    @api.multi
    def activeCyclosUser(self):
        for record in self:
            data = {
                'status': 'active',
                'comment': 'Disable by Odoo'
            }
            res = record._cyclos_rest_call(
                'POST',
                '/%s/status' % record.cyclos_id,
                data=data)
            record.write({
                'cyclos_active': True,
                'cyclos_status': 'active',
            })
            _logger.debug("res: %s" % res)

    @api.multi
    def blockCyclosUser(self):
        for record in self:
            data = {
                'status': 'blocked',
                'comment': 'Blocked by Odoo'
            }
            res = record._cyclos_rest_call(
                'POST',
                '/%s/status' % record.cyclos_id,
                data=data)
            record.write({
                'cyclos_active': False,
                'cyclos_status': 'Blocked',
            })
            _logger.debug("res: %s" % res)

    @api.multi
    def disableCyclosUser(self):
        for record in self:
            data = {
                'status': 'disabled',
                'comment': 'Disable by Odoo'
            }
            res = record._cyclos_rest_call(
                'POST',
                '/%s/status' % record.cyclos_id,
                data=data)
            record.write({
                'cyclos_active': False,
                'cyclos_status': 'disabled',
            })
            _logger.debug("res: %s" % res)

    def forceCyclosPassword(self, password):
        for record in self:
            # TODO: need to stock password type id from cyclos API and replace -4307382460900696903
            data = {
                    "newPassword": password,
                    "checkConfirmation": True,
                    "newPasswordConfirmation": password,
                    "forceChange": False
                    }
            try:
                record._cyclos_rest_call(
                    'POST',
                    '/%s/passwords/%s/change' % (record.cyclos_id, '-4307382460900696903'),
                    data=data)
            except ValueError as e:
                if (len(e.args) > 1 and
                    e.args[1].status_code == 422 and
                    'newPassword' in e.args[1].json().get('properties', [])):
                    _logger.debug("Ignoring Cyclos NewPassword Error !")
                else:
                    raise

    def createCyclosUserToken(self, api_login, api_password):
        self.ensure_one()
        for record in self:
            res = record._cyclos_rest_call(
                'POST',
                '/auth/session',
                data={'timeoutInSeconds': 90000},
                api_login=api_login,
                api_password=api_password)
            _logger.debug("res TOKEN: %s" % res.text)
            data = json.loads(res.text)
            return data.get('sessionToken', False)

    @api.multi
    def removeCyclosUserToken(self, api_login, api_password):
        for record in self:
            res = record._cyclos_rest_call(
                'DELETE',
                '/auth/session',
                api_login=api_login,
                api_password=api_password)
            _logger.debug("res: %s" % res.text)
