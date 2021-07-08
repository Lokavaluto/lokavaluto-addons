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
        if method == 'POST':
            return requests.post(api_url,
                                 auth=HTTPBasicAuth(api_login, api_password),
                                 verify=False,
                                 data=json.dumps(data),
                                 headers=headers)
        if method == 'GET':
            return requests.get(api_url,
                                auth=HTTPBasicAuth(api_login, api_password),
                                verify=False,
                                data=json.dumps(data),
                                headers=headers)
        if method == 'DELETE':
            return requests.delete(api_url,
                                   auth=HTTPBasicAuth(api_login, api_password),
                                   verify=False,
                                   data=json.dumps(data),
                                   headers=headers)

    def _update_auth_data(self, password):
        self.ensure_one()
        data = super(ResPartner, self)._update_auth_data(password)
        # Update cyclos password with odoo one from authenticate session
        self.forceCyclosPassword(password)
        new_token = self.createCyclosUserToken(self.id, password)
        if new_token:
            cyclos_data = {
                'type': 'cyclos',
                'user_accounts': [
                    {
                        'owner_id': self.cyclos_id,
                        'token': new_token,
                        'url': self.env.user.company_id.cyclos_server_url,
                    }
                ]        
            }
            data.append(cyclos_data)
        return data

    def _get_backend_credentials(self):
        self.ensure_one()
        data = super(ResPartner, self)._get_backend_credentials()
        parsed_uri = urlparse(self.env.user.company_id.cyclos_server_url)
        if self.cyclos_id and parsed_uri:
            cyclos_data = {
                'type': 'cyclos',
                'user_accounts': [{
                    'url': self.env.user.company_id.cyclos_server_url,
                    'owner_id': self.cyclos_id,
                }]
            }
        data.append(cyclos_data)
        return data

    def _update_search_data(self, backend_keys):
        self.ensure_one()
        _logger.debug('SEARCH: backend_keys = %s' % backend_keys)
        data = super(ResPartner, self)._update_search_data(backend_keys)
        for backend_key in backend_keys:
            if "cyclos" in backend_key and self.cyclos_id:
                data[backend_key] = [self.cyclos_id]
        _logger.debug('SEARCH: data %s' % data)
        return data

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
            res = record._cyclos_rest_call('POST', '/users', data=data)
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

    def forceCyclosPassword(self, password):
        for record in self:
            # TODO: need to stock password type id from cyclos API and replace -4307382460900696903
            data = {
                    "newPassword": password,
                    "checkConfirmation": True,
                    "newPasswordConfirmation": password,
                    "forceChange": False
                    }
            res = record._cyclos_rest_call(
                'POST',
                '/%s/passwords/%s/change' % (record.cyclos_id, '-4307382460900696903'),
                data=data)
            _logger.debug("forceCyclosPassword res: %s" % res.text)

    def createCyclosUserToken(self, api_login, api_password):
        self.ensure_one()
        for record in self:
            res = record._cyclos_rest_call(
                'POST',
                '/auth/session',
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

