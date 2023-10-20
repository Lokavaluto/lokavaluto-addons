from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Inherits partner:
    - add comchain fields in the partner form
    - add functions"""

    _inherit = "res.partner"

    def _update_auth_data(self, password):
        self.ensure_one()
        data = super(ResPartner, self)._update_auth_data(password)
        backend_data = self.get_wallet("comchain")
        data.extend(backend_data.comchain_backend_accounts_data)
        return data

    def _update_search_data(self, backend_keys):
        self.ensure_one()
        _logger.debug("SEARCH: backend_keys = %s" % backend_keys)
        data = super(ResPartner, self)._update_search_data(backend_keys)
        backend_data = self.get_wallet("comchain")
        for backend_key in backend_keys:
            if backend_key.startswith("comchain:") and backend_data:
                data[backend_key] = [backend_data.comchain_id]
        _logger.debug("SEARCH: data %s" % data)
        return data

    def _get_backend_credentials(self):
        self.ensure_one()
        data = super(ResPartner, self)._get_backend_credentials()
        backend_data = self.get_wallet("comchain")
        data.extend(backend_data.comchain_backend_accounts_data)
        return data

    def backends(self):
        self.ensure_one()
        backends = super(ResPartner, self).backends()
        backend_data = self.get_wallet("comchain")
        if not backend_data.comchain_id:
            return backends
        backend_id = backend_data.comchain_backend_id
        if not backend_id:
            ## not present in wallet and not configured in general settings
            return backends
        return backends | {backend_id}

    ## XXXvlab: currently not used ??
    @api.multi
    def activate_comchain_user(self, params):
        self.ensure_one()
        backend_data = self.get_wallet("comchain")
        backend_data.write(
            {
                "comchain_status": "active",
                "comchain_type": "%s" % params.type,
                "comchain_credit_min": params.credit_min,
                "comchain_credit_max": params.credit_max,
            }
        )

    def show_app_access_buttons(self):
        # For comchain the app access buttons on the portal are always displayed
        # as long as the comchain currency is defined,
        # as the user needs to connect to Monujo to create its wallet
        res = super(ResPartner, self).show_app_access_buttons()
        if self.env.user.company_id.comchain_currency_name:
            res = True
        return res
