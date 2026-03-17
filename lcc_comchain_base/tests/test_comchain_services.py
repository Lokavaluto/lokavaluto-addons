import json

from odoo.addons.component.tests.common import TransactionComponentCase
from odoo.addons.lcc_comchain_base.datamodel.comchain import ComchainRegisterInfo


class TestComchainServiceRegister(TransactionComponentCase):
    def _get_service_as_user(self, user):
        collection = self.env["lokavaluto.private.services"].with_user(user).browse(1)
        with collection.work_on("res.partner.backend") as work:
            return work.component(usage="comchain")

    def test_register_unknown_currency_returns_error(self):
        """Registering a wallet on a non-existent currency returns
        a JSON error dict with the currency name."""

        user = self.env["res.users"].create({"name": "Alice", "login": "alice"})
        service = self._get_service_as_user(user)

        wallet_data = json.dumps({"server": {"name": "NonExistentCoin"}})
        params = ComchainRegisterInfo(
            address="0xdeadbeef",
            wallet=wallet_data,
            message_key="testkey",
        )

        result = service.register(params)
        self.assertEqual(result["status"], "Error")
        self.assertIn("NonExistentCoin", result["error"])
        self.assertIn("not found", result["error"])
