import json
from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    ''' Inherits partner:
        - add comchain fields in the partner form
        - add functions'''
    _inherit = 'res.partner'

    comchain_active = fields.Boolean(string='comchain OK')
    comchain_id = fields.Char(string="Address")
    comchain_wallet = fields.Text(string="Crypted json wallet")
    comchain_status = fields.Char(string="Comchain Status")
    comchain_type = fields.Selection([
        ('0', 'Personal'),
        ('1', 'Company'),
        ('2', 'Admin')
    ], string='Type', groups="lcc_comchain_base.group_comchain_manager")
    comchain_credit_min = fields.Float(string="Min Credit limit",
                                       groups="lcc_comchain_base.group_comchain_manager")
    comchain_credit_max = fields.Float(string="Max Credit limit",
                                       groups="lcc_comchain_base.group_comchain_manager")
    comchain_message_key = fields.Char(string="Message keys")

    @api.multi
    def open_commercial_member_entity(self):
        """ Utility method:
            - add an "Open Company" button in partner views """
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
        if self.comchain_id:
            data.append(self._comchain_backend_data())
        return data

    def _comchain_backend_data(self):
        """Prepare backend data to be sent by credentials requests"""
        wallet = json.loads(self.comchain_wallet) if self.comchain_wallet else {}
        currency_name = wallet.get("server", {}).get("name", {}) or \
            self.env.user.company_id.comchain_currency_name

        data = {
            'type': 'comchain:%s' % currency_name,
            'accounts': []
        }
        if wallet:
            data['accounts'].append({
                'wallet': wallet,
                'message_key': self.comchain_message_key
            })
        return data

    def _update_search_data(self, backend_keys):
        self.ensure_one()
        _logger.debug('SEARCH: backend_keys = %s' % backend_keys)
        data = super(ResPartner, self)._update_search_data(backend_keys)
        for backend_key in backend_keys:
            if backend_key.startswith("comchain:") and self.comchain_id:
                data[backend_key] = [self.comchain_id]
        _logger.debug('SEARCH: data %s' % data)
        return data

    def _get_backend_credentials(self):
        self.ensure_one()
        data = super(ResPartner, self)._get_backend_credentials()
        if self.comchain_id:
            data.append(self._comchain_backend_data())
        return data

    def backends(self):
        self.ensure_one()
        backends = super(ResPartner, self).backends()
        if self.comchain_id:
            return backends | {"comchain"}
        else:
            return backends

    @api.multi
    def validatecomchainUser(self):
        for record in self:
            record.write({
                'comchain_active': True,
                'comchain_status': "actif",
            })
