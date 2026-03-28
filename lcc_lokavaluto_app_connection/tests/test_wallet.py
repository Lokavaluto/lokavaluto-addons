from types import SimpleNamespace

from odoo.exceptions import MissingError
from odoo.tests.common import TransactionCase


class TestWalletGetByUri(TransactionCase):
    """Test res.partner.backend.get_by_uri."""

    def setUp(self):
        super().setUp()
        currency_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        self.currency = self.env["res.alt.currency"].create(
            {
                "name": "Test Currency",
                "ident": "testcurrency",
                "active": True,
                "engine": "foo",
                "currency_unit_product_id": currency_product.id,
            }
        )

    ## Helpers

    def _make_user_and_wallet(self, login, addr=None):
        if addr is None:
            addr = f"0x{login}"
        user = self.env["res.users"].create(
            {"name": login.capitalize(), "login": login}
        )
        wallet = self.env["res.partner.backend"].create(
            {
                "partner_id": user.partner_id.id,
                "name": f"foo:{addr}",
                "ident": addr,
                "alt_currency_id": self.currency.id,
            }
        )
        wallet.status = "active"
        return SimpleNamespace(user=user, wallet=wallet)

    ## Tests

    def test_get_by_uri_returns_wallet(self):
        alice = self._make_user_and_wallet("alice")
        uri = f"{self.currency.uri}/wallet/0xalice"
        wallet = self.env["res.partner.backend"].get_by_uri(uri)
        self.assertEqual(wallet.id, alice.wallet.id)

    def test_get_by_uri_unknown_currency(self):
        self._make_user_and_wallet("alice")
        with self.assertRaises(MissingError):
            self.env["res.partner.backend"].get_by_uri(
                "foo://nonexistent/wallet/0xalice"
            )

    def test_get_by_uri_unknown_wallet(self):
        self._make_user_and_wallet("alice")
        with self.assertRaises(MissingError):
            self.env["res.partner.backend"].get_by_uri(
                f"{self.currency.uri}/wallet/0xnonexistent"
            )

    def test_get_by_uri_malformed(self):
        self._make_user_and_wallet("alice")
        with self.assertRaises(MissingError):
            self.env["res.partner.backend"].get_by_uri("garbage")
