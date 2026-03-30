import json

from odoo.addons.component.tests.common import TransactionComponentCase
from odoo.addons.lcc_comchain_base.datamodel.comchain import ComchainRegisterInfo


class TestComchainServiceRegister(TransactionComponentCase):

    def _get_service_as_user(self, user):
        collection = self.env["lokavaluto.private.services"].with_user(user).browse(1)
        with collection.work_on("res.partner.backend") as work:
            return work.component(usage="comchain")

    def _make_currency(self, ident="testcc"):
        currency_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        return self.env["res.alt.currency"].create(
            {
                "name": "Test Comchain",
                "ident": ident,
                "active": True,
                "engine": "comchain",
                "currency_unit_product_id": currency_product.id,
            }
        )

    def _make_register_params(self, currency_ident, address="0xabc", message_key="testkey"):
        wallet_data = json.dumps({"server": {"name": currency_ident}})
        return ComchainRegisterInfo(
            address=address,
            wallet=wallet_data,
            message_key="testkey",
        )

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

    def test_register_sets_type_field(self):
        """Registering a wallet via the register endpoint should
        populate the stored related field 'type' from the currency engine."""

        self._make_currency("testcc")
        alice = self.env["res.users"].create({"name": "Alice", "login": "alice"})
        service = self._get_service_as_user(alice)

        result = service.register(
            self._make_register_params("testcc", address="0xdeadbeef")
        )
        self.assertTrue(result)

        wallet = self.env["res.partner.backend"].search(
            [("comchain_id", "=", "0xdeadbeef")]
        )
        self.assertEqual(len(wallet), 1)
        self.assertEqual(wallet.type, "comchain")
        self.assertEqual(wallet.status, "to_confirm")

    def test_register_reactivates_archived_wallet(self):
        """Re-registering an archived wallet reactivates it."""

        currency = self._make_currency("testcc")
        alice = self.env["res.users"].create({"name": "Alice", "login": "alice"})

        # Create and archive a wallet
        wallet = self.env["res.partner.backend"].create(
            {
                "partner_id": alice.partner_id.id,
                "name": "comchain:0xabc",
                "ident": "0xabc",
                "alt_currency_id": currency.id,
                "comchain_id": "0xabc",
                "comchain_status": "disabled",
                "comchain_wallet": "{}",
                "comchain_message_key": "oldkey",
            }
        )
        wallet.active = False

        # Re-register same address
        service = self._get_service_as_user(alice)
        result = service.register(self._make_register_params("testcc", address="0xabc", message_key="testkey"))

        self.assertTrue(result)
        wallet.invalidate_recordset()
        wallet = (
            self.env["res.partner.backend"]
            .with_context(active_test=False)
            .browse(wallet.id)
        )
        self.assertTrue(wallet.active)
        self.assertEqual(wallet.comchain_status, "pending")
        self.assertEqual(wallet.comchain_message_key, "testkey")

    def test_register_refuses_active_duplicate(self):
        """Registering an already active wallet returns error."""

        currency = self._make_currency()
        alice = self.env["res.users"].create({"name": "Alice", "login": "alice"})

        # Create an active wallet
        self.env["res.partner.backend"].create(
            {
                "partner_id": alice.partner_id.id,
                "name": "comchain:0xabc",
                "ident": "0xabc",
                "alt_currency_id": currency.id,
                "comchain_id": "0xabc",
                "comchain_status": "active",
                "comchain_wallet": "{}",
                "comchain_message_key": "key",
            }
        )

        service = self._get_service_as_user(alice)
        result = service.register(self._make_register_params("testcc", address="0xabc"))

        self.assertEqual(result["status"], "Error")
        self.assertIn("already registered", result["error"])

    def test_register_allows_archived_wallet_from_other_user(self):
        """Registering an address archived by another user creates a new wallet."""

        currency = self._make_currency()
        alice = self.env["res.users"].create({"name": "Alice", "login": "alice"})
        bob = self.env["res.users"].create({"name": "Bob", "login": "bob"})

        # Bob owns an archived wallet
        wallet = self.env["res.partner.backend"].create(
            {
                "partner_id": bob.partner_id.id,
                "name": "comchain:0xabc",
                "ident": "0xabc",
                "alt_currency_id": currency.id,
                "comchain_id": "0xabc",
                "comchain_status": "disabled",
                "comchain_wallet": "{}",
                "comchain_message_key": "key",
            }
        )
        wallet.active = False

        # Alice registers the same address — succeeds
        service = self._get_service_as_user(alice)
        result = service.register(self._make_register_params("testcc"))
        self.assertTrue(result)

        # Alice has her own wallet now
        alice_wallet = self.env["res.partner.backend"].search(
            [
                ("comchain_id", "=", "0xabc"),
                ("partner_id", "=", alice.partner_id.id),
            ]
        )
        self.assertEqual(len(alice_wallet), 1)
        self.assertEqual(alice_wallet.comchain_status, "pending")

    def test_register_refuses_active_wallet_from_other_user(self):
        """Registering an address active on another user returns error."""

        currency = self._make_currency()
        alice = self.env["res.users"].create({"name": "Alice", "login": "alice"})
        bob = self.env["res.users"].create({"name": "Bob", "login": "bob"})

        # Bob owns an active wallet
        self.env["res.partner.backend"].create(
            {
                "partner_id": bob.partner_id.id,
                "name": "comchain:0xabc",
                "ident": "0xabc",
                "alt_currency_id": currency.id,
                "comchain_id": "0xabc",
                "comchain_status": "active",
                "comchain_wallet": "{}",
                "comchain_message_key": "key",
            }
        )

        # Alice tries to register the same address — refused
        service = self._get_service_as_user(alice)
        result = service.register(self._make_register_params("testcc"))

        self.assertEqual(result["status"], "Error")
        self.assertIn("another user", result["error"])
