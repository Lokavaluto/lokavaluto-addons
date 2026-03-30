from types import SimpleNamespace

from odoo.addons.component.tests.common import TransactionComponentCase


class TestComchainPermissions(TransactionComponentCase):
    """Test per-currency permissions derived from comchain_type."""

    def setUp(self):
        super().setUp()
        currency_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        self.comchain_currency = self.env["res.alt.currency"].create(
            {
                "name": "Test Comchain",
                "ident": "testcomchain",
                "active": True,
                "engine": "comchain",
                "currency_unit_product_id": currency_product.id,
            }
        )
        self.currency_ident = "testcomchain"

    ## Helpers

    def _make_user_and_wallet(self, login, comchain_type="0", addr="0xabc"):
        """Helper to create a user and associated comchain wallet."""
        user = self._make_users(login)
        user_uri = self._user_uri(addr)
        wallet = self._make_comchain_wallet(
            user, comchain_type=comchain_type, addr=addr
        )
        user_ident = wallet.ident
        return SimpleNamespace(
            user=user,
            user_uri=user_uri,
            user_ident=user_ident,
            wallet=wallet,
        )

    def _make_users(self, *logins):
        users = []
        for login in logins:
            user = self.env["res.users"].create(
                {"name": login.capitalize(), "login": login}
            )
            users.append(user)
        return users[0] if len(logins) == 1 else users

    def _make_comchain_wallet(self, user, comchain_type="0", addr="0xabc"):
        return self.env["res.partner.backend"].create(
            {
                "partner_id": user.partner_id.id,
                "name": f"comchain:{addr}",
                "ident": addr,
                "alt_currency_id": self.comchain_currency.id,
                "comchain_type": comchain_type,
                "comchain_status": "active",
            }
        )

    def _user_uri(self, addr):
        """Build a user_uri for the given user on the test currency."""
        return f"comchain://testcomchain/user/{addr}"

    ## Tests: get_auth_context

    def test_get_auth_context_per_comchain_type(self):
        """get_auth_context returns comchain_perms based on comchain_type."""
        expected = {
            "0": (),
            "1": (),
            "2": ("set_admin", "set_property", "pledge"),
            "3": ("pledge",),
            "4": ("set_property",),
        }
        for comchain_type, expected_perms in expected.items():
            with self.subTest(comchain_type=comchain_type):
                alice = self._make_user_and_wallet(
                    f"alice_{comchain_type}",
                    comchain_type=comchain_type,
                )
                auth = alice.wallet.get_auth_context()
                self.assertEqual(auth["comchain_perms"], expected_perms)

    def test_get_auth_context_legacy_full_manager(self):
        """Legacy group_wallet_full_manager gets full perms regardless of type."""
        alice = self._make_user_and_wallet("alice", comchain_type="0")
        alice.user.groups_id = [
            (
                4,
                self.env.ref(
                    "lcc_lokavaluto_app_connection.group_wallet_full_manager"
                ).id,
            )
        ]
        auth = alice.wallet.get_auth_context()
        self.assertEqual(
            auth["comchain_perms"],
            ("set_admin", "set_property", "pledge"),
        )

    def test_get_auth_context_no_comchain_type_defaults_empty(self):
        """Wallet with no comchain_type returns empty perms tuple."""
        alice = self._make_user_and_wallet("alice", comchain_type=False)
        auth = alice.wallet.get_auth_context()
        self.assertEqual(auth["comchain_perms"], ())
