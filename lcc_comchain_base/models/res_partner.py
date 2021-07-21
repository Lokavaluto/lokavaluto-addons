import json
from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    ''' Inherits partner, adds comchain fields in the partner form, and functions'''
    _inherit = 'res.partner'

    comchain_active = fields.Boolean(string='comchain OK')
    comchain_id = fields.Char(string="Address")
    comchain_wallet = fields.Text(string="Crypted json wallet")
    comchain_status = fields.Char(string="Comchain Status")
    comchain_type = fields.Selection([
        ('0', 'Personal'),
        ('1', 'Company'),
        ('2', 'Admin')
    ], string='Type')
    comchain_credit_min = fields.Float(string="Min Credit limit")
    comchain_credit_max = fields.Float(string="Max Credit limit")

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

    def _update_auth_data(self, password):
        self.ensure_one()
        data = super(ResPartner, self)._update_auth_data(password)
        # Update comchain password with odoo one from authenticate session
        if self.comchain_id:
            comchain_data = {
                'type': 'comchain',
                'bank_accounts': [json.loads(self.comchain_wallet),]
            }
            data.append(comchain_data)
            return data
        return []

    def _update_search_data(self, backend_keys):
        self.ensure_one()
        _logger.debug('SEARCH: backend_keys = %s' % backend_keys)
        data = super(ResPartner, self)._update_search_data(backend_keys)
        for backend_key in backend_keys:
            if "comchain" in backend_key and self.comchain_id:
                data[backend_key] = [self.comchain_id]
        _logger.debug('SEARCH: data %s' % data)
        return data

    def _get_backend_credentials(self):
        self.ensure_one()
        data = super(ResPartner, self)._get_backend_credentials()
        if self.comchain_id:
            comchain_data = {
                'type': 'comchain',
                'bank_accounts': [json.loads(self.comchain_wallet),]
            }
        data.append(comchain_data)
        return data

    def _has_backend_account_activated(self, backend_keys):
        self.ensure_one()
        response = super(ResPartner, self)._has_backend_account_activated(backend_keys)
        for backend_key in backend_keys:
            if "comchain" in backend_key and self.comchain_id:
                response = True
        return response

    @api.multi
    def validatecomchainUser(self):
        for record in self:
            record.write({
                'comchain_active': True,
                'comchain_status': "actif",
            })