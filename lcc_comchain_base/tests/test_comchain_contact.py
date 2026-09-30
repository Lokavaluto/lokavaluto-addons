from odoo.addons.component.tests.common import TransactionComponentCase
from odoo.addons.lcc_lokavaluto_app_connection.tests.common import WalletContactTestMixin

from ..datamodel.comchain import ComchainPartnersInfo


class TestComchainServiceContact(WalletContactTestMixin, TransactionComponentCase):
    wallet_type = "comchain"
    identifier_field = "comchain_id"
    contact_params_class = ComchainPartnersInfo
    address = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
