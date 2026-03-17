import json

from odoo.addons.component.tests.common import TransactionComponentCase
from odoo.addons.lcc_comchain_base.datamodel.comchain import ComchainRegisterInfo


class TestComchainServiceCanActivate(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        self.user = self.env["res.users"].create(
            {"name": "Regular User", "login": "regular_user"}
        )
        self.user_accounts_manager = self.env["res.users"].create(
            {
                "name": "Accounts Manager",
                "login": "accounts_manager",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref(
                                "lcc_lokavaluto_app_connection"
                                ".group_wallet_accounts_manager"
                            ).id
                        ],
                    )
                ],
            }
        )

    def _get_service_as_user(self, user):
        collection = self.env["lokavaluto.private.services"].with_user(user).browse(1)
        with collection.work_on("res.partner.backend") as work:
            return work.component(usage="comchain")

    def test_can_activate_as_accounts_manager(self):
        """A user with group_wallet_accounts_manager can activate accounts."""
        service = self._get_service_as_user(self.user_accounts_manager)
        self.assertTrue(service.can_activate())

    def test_can_activate_as_regular_user(self):
        """A regular user cannot activate accounts."""
        service = self._get_service_as_user(self.user)
        self.assertFalse(service.can_activate())


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
