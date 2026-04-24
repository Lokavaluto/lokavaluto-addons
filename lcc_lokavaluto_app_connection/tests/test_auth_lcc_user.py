from types import SimpleNamespace

from odoo.tests.common import TransactionCase


class TestWalletAuthBase(TransactionCase):
    """Test base get_auth_context and get_authorized_actions stubs on res.partner.backend."""

    def setUp(self):
        super().setUp()
        ## This test asserts ``get_authorized_actions()`` returns the
        ## default empty list for a wallet with no reconversion rule
        ## match; purge pre-existing rules so the default is reliable.
        self.env["reconversion.rule"].search([]).unlink()

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
        """Helper to create a user and associated wallet."""
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

    def test_get_auth_context_returns_empty_dict(self):
        alice = self._make_user_and_wallet("alice")
        result = alice.wallet.get_auth_context()
        self.assertEqual(result, {})

    def test_get_auth_context_ensures_one(self):
        empty = self.env["res.partner.backend"].browse()
        with self.assertRaises(ValueError):
            empty.get_auth_context()

    def test_get_authorized_actions_returns_empty_list(self):
        alice = self._make_user_and_wallet("alice")
        result = alice.wallet.get_authorized_actions()
        self.assertEqual(result, [])

    def test_get_authorized_actions_ensures_one(self):
        empty = self.env["res.partner.backend"].browse()
        with self.assertRaises(ValueError):
            empty.get_authorized_actions()
