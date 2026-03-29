from types import SimpleNamespace
from unittest.mock import patch

from minimock import Mock

from odoo.exceptions import AccessDenied, MissingError
from odoo.addons.component.tests.common import TransactionComponentCase

import odoo.addons.lcc_lokavaluto_app_connection.services as svc


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

    def _get_wallet_service(self, user):
        collection = self.env["lokavaluto.private.services"].with_user(user).browse(1)
        with collection.work_on("res.partner.backend") as work:
            return work.component(usage="wallet")

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

    ## Tests: get_authorized_actions

    def test_get_authorized_actions_per_comchain_type(self):
        """get_authorized_actions maps comchain_type to actions."""
        expected = {
            "0": [],
            "1": [],
            "2": [
                "activate",
                "search-all-recipients",
                "validate-credit-request",
            ],
            "3": ["validate-credit-request"],
            "4": ["activate", "search-all-recipients"],
        }
        for comchain_type, expected_actions in expected.items():
            with self.subTest(comchain_type=comchain_type):
                alice = self._make_user_and_wallet(
                    f"alice_{comchain_type}",
                    comchain_type=comchain_type,
                )
                actions = alice.wallet.get_authorized_actions()
                self.assertEqual(actions, expected_actions)

    def test_get_authorized_actions_legacy_full_manager(self):
        """Legacy group_wallet_full_manager gets all actions."""
        alice = self._make_user_and_wallet("alice", comchain_type="0")
        alice.user.groups_id = [
            (
                4,
                self.env.ref(
                    "lcc_lokavaluto_app_connection.group_wallet_full_manager"
                ).id,
            )
        ]
        actions = alice.wallet.get_authorized_actions()
        self.assertEqual(
            actions,
            ["activate", "search-all-recipients", "validate-credit-request"],
        )

    def test_get_authorized_actions_personal_has_no_actions(self):
        """Personal wallet (type 0) has no permissions, thus no actions."""
        alice = self._make_user_and_wallet("alice", comchain_type="0")
        actions = alice.wallet.get_authorized_actions()
        self.assertEqual(actions, [])

    def test_get_authorized_actions_disabled_has_no_actions(self):
        """Disabled wallet has no actions regardless of type."""
        alice = self._make_user_and_wallet(
            "alice", comchain_type="2", comchain_status="disabled"
        )
        actions = alice.wallet.get_authorized_actions()
        self.assertEqual(actions, [])

    ## Tests: wallet service archive endpoint

    def _call_archive(self, caller, wallet_ident, features_header=None):
        """Call the archive endpoint via the wallet service."""
        headers = {"X-Lokapi-Caller-User-Uri": caller.user_uri}
        if features_header:
            headers["X-Client-Features"] = features_header
        mock_request = Mock(
            "request",
            httprequest=Mock("httprequest", headers=headers),
            future_response=Mock("future_response", headers={}),
            _common_features=None,
        )
        service = self._get_wallet_service(caller.user)
        with patch.object(svc, "request", mock_request):
            return service.archive(wallet_ident)

    def test_ws_archive_disabled_wallet(self):
        """Admin can archive a disabled (non-archived) wallet."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        bob = self._make_user_and_wallet("bob", addr="0xb", comchain_status="disabled")

        self._call_archive(alice, "0xb", features_header="wallet/0")

        wallet_bob = (
            self.env["res.partner.backend"]
            .with_context(active_test=False)
            .browse(bob.wallet.id)
        )
        self.assertEqual(wallet_bob.comchain_status, "inactive")
        self.assertFalse(wallet_bob.active)

    def test_ws_archive_admin_can_archive_personal(self):
        """Admin can archive a personal wallet via wallet service."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        self._call_archive(alice, "0xb", features_header="wallet/0")

        wallet_bob = (
            self.env["res.partner.backend"]
            .with_context(active_test=False)
            .browse(bob.wallet.id)
        )
        self.assertEqual(wallet_bob.comchain_status, "inactive")
        self.assertFalse(wallet_bob.active)

    def test_ws_archive_property_can_archive_personal(self):
        """Property admin can archive a personal wallet via wallet service."""
        alice = self._make_user_and_wallet("alice", comchain_type="4", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        self._call_archive(alice, "0xb", features_header="wallet/0")

        wallet_bob = (
            self.env["res.partner.backend"]
            .with_context(active_test=False)
            .browse(bob.wallet.id)
        )
        self.assertEqual(wallet_bob.comchain_status, "inactive")
        self.assertFalse(wallet_bob.active)

    def test_ws_archive_property_cannot_archive_admin(self):
        """Property admin cannot archive an admin-type wallet."""
        alice = self._make_user_and_wallet("alice", comchain_type="4", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="2", addr="0xb")

        with self.assertRaises(AccessDenied):
            self._call_archive(alice, "0xb", features_header="wallet/0")

    def test_ws_archive_personal_denied(self):
        """Personal user (no perms) cannot archive via wallet service."""
        alice = self._make_user_and_wallet("alice", comchain_type="0", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        with self.assertRaises(AccessDenied):
            self._call_archive(alice, "0xb", features_header="wallet/0")

    def test_ws_archive_pledge_denied(self):
        """Pledge user cannot archive via wallet service."""
        alice = self._make_user_and_wallet("alice", comchain_type="3", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        with self.assertRaises(AccessDenied):
            self._call_archive(alice, "0xb", features_header="wallet/0")

    def test_ws_archive_nonexistent_wallet(self):
        """Archiving a nonexistent wallet raises MissingError."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")

        with self.assertRaises(MissingError):
            self._call_archive(alice, "0xnonexistent", features_header="wallet/0")

    ## Tests: auth_context endpoint (comchain wallet service)

    def _call_auth_context(self, caller, target_ident, features_header=None):
        """Call the comchain auth_context endpoint."""
        headers = {"X-Lokapi-Caller-User-Uri": caller.user_uri}
        if features_header:
            headers["X-Client-Features"] = features_header
        mock_request = Mock(
            "request",
            httprequest=Mock("httprequest", headers=headers),
            future_response=Mock("future_response", headers={}),
            _common_features=None,
        )
        service = self._get_wallet_service(caller.user)
        with patch.object(svc, "request", mock_request):
            return service.auth_context(target_ident)

    def test_auth_context_returns_target_perms(self):
        """auth_context returns the TARGET wallet's auth_context."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="3", addr="0xb")
        result = self._call_auth_context(alice, "0xb", features_header="wallet/0")
        self.assertEqual(result, ["pledge"])

    def test_auth_context_unknown_wallet_raises(self):
        """Unknown wallet ident raises MissingError."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        with self.assertRaises(MissingError):
            self._call_auth_context(alice, "0xnonexistent", features_header="wallet/0")

    def test_auth_context_requires_actions(self):
        """Caller with no actions is rejected (require_actions=True)."""
        alice = self._make_user_and_wallet("alice", comchain_type="0", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")
        with self.assertRaises(AccessDenied):
            self._call_auth_context(alice, "0xb", features_header="wallet/0")
