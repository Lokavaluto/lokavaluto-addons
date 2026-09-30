from odoo.addons.component.tests.common import TransactionComponentCase
from odoo.addons.lcc_lokavaluto_app_connection.tests.common import WalletContactTestMixin

from ..datamodel.cyclos import CyclosPartnersInfo


class TestCyclosServiceContact(WalletContactTestMixin, TransactionComponentCase):
    wallet_type = "cyclos"
    identifier_field = "cyclos_id"
    contact_params_class = CyclosPartnersInfo
    address = "123456"
