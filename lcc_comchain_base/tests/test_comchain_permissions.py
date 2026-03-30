from types import SimpleNamespace
from unittest.mock import patch

from odoo.exceptions import AccessDenied, MissingError, ValidationError

import odoo.addons.lcc_lokavaluto_app_connection.services as svc

from .common import ComchainTestCase


class TestComchainPermissions(ComchainTestCase):
    """Test per-currency permissions derived from comchain_type."""

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

    ## Tests: wallet service update endpoint

    def _call_update(self, caller, wallet_ident, data, features_header=None):
        """Call the update endpoint via the wallet service."""
        mock_request = self._mock_request(caller, features_header=features_header)
        service = self._get_wallet_service(caller.user)
        params = SimpleNamespace(data=data)
        with patch.object(svc, "request", mock_request):
            return service.update(wallet_ident, params)

    def test_ws_update_admin_can_set_admin_type(self):
        """Admin can set admin account types via wallet service."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        self._call_update(alice, "0xb", {"accountType": 2}, features_header="wallet/0")
        self.assertEqual(bob.wallet.comchain_type, "2")

    def test_ws_update_property_can_set_professional(self):
        """Property admin can set non-admin account types."""
        alice = self._make_user_and_wallet("alice", comchain_type="4", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        self._call_update(alice, "0xb", {"accountType": 1}, features_header="wallet/0")
        self.assertEqual(bob.wallet.comchain_type, "1")

    def test_ws_update_sets_comchain_status(self):
        """wallet service update writes comchain_status from status."""
        alice = self._make_user_and_wallet("alice", comchain_type="4", addr="0xa")
        bob = self._make_user_and_wallet("bob", addr="0xb")

        self._call_update(
            alice, "0xb", {"status": "disabled"}, features_header="wallet/0"
        )
        self.assertEqual(bob.wallet.comchain_status, "disabled")

    def test_ws_update_sets_credit_limits(self):
        """wallet service update writes credit limits."""
        alice = self._make_user_and_wallet("alice", comchain_type="4", addr="0xa")
        bob = self._make_user_and_wallet("bob", addr="0xb")

        self._call_update(
            alice,
            "0xb",
            {"lowLimit": -500.0, "highLimit": 1000.0},
            features_header="wallet/0",
        )
        self.assertEqual(bob.wallet.comchain_credit_min, -500.0)
        self.assertEqual(bob.wallet.comchain_credit_max, 1000.0)

    def test_ws_update_disabled_wallet(self):
        """Admin can update a disabled (non-archived) wallet."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        bob = self._make_user_and_wallet("bob", addr="0xb", comchain_status="disabled")

        self._call_update(alice, "0xb", {"accountType": 1}, features_header="wallet/0")
        self.assertEqual(bob.wallet.comchain_type, "1")

    def test_ws_update_personal_denied(self):
        """Personal user cannot update via wallet service."""
        alice = self._make_user_and_wallet("alice", comchain_type="0", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        with self.assertRaises(AccessDenied):
            self._call_update(
                alice, "0xb", {"accountType": 1}, features_header="wallet/0"
            )

    def test_ws_update_property_cannot_promote_to_admin(self):
        """Property admin cannot promote to admin types via wallet service."""
        alice = self._make_user_and_wallet("alice", comchain_type="4", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        for admin_type in (2, 3, 4):
            with self.assertRaises(AccessDenied):
                self._call_update(
                    alice,
                    "0xb",
                    {"accountType": admin_type},
                    features_header="wallet/0",
                )

    def test_ws_update_property_cannot_set_status_on_admin(self):
        """Property admin cannot change status on admin-type wallet."""
        alice = self._make_user_and_wallet("alice", comchain_type="4", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="2", addr="0xb")

        with self.assertRaises(AccessDenied):
            self._call_update(
                alice, "0xb", {"status": "disabled"}, features_header="wallet/0"
            )

    def test_ws_update_invalid_account_type_not_int(self):
        """accountType must be an integer."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        with self.assertRaises(ValidationError):
            self._call_update(
                alice, "0xb", {"accountType": "admin"}, features_header="wallet/0"
            )

    def test_ws_update_invalid_account_type_unknown(self):
        """Unknown accountType integer raises ValidationError."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        with self.assertRaises(ValidationError):
            self._call_update(
                alice, "0xb", {"accountType": 99}, features_header="wallet/0"
            )

    def test_ws_update_nonexistent_wallet(self):
        """Updating a nonexistent wallet raises MissingError."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")

        with self.assertRaises(MissingError):
            self._call_update(
                alice, "0xnonexistent", {"accountType": 1}, features_header="wallet/0"
            )

    def test_ws_update_pledge_denied(self):
        """Pledge user cannot update via wallet service."""
        alice = self._make_user_and_wallet("alice", comchain_type="3", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        with self.assertRaises(AccessDenied):
            self._call_update(
                alice, "0xb", {"accountType": 1}, features_header="wallet/0"
            )

    def test_ws_update_permissions_change_on_type_update(self):
        """Changing comchain_type via update changes permissions."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        # Bob starts with no permissions
        result = self._call_auth_context(alice, "0xb", features_header="wallet/0")
        self.assertEqual(result, [])

        # Alice upgrades Bob to admin
        self._call_update(alice, "0xb", {"accountType": 2}, features_header="wallet/0")

        # Bob now has admin permissions
        result = self._call_auth_context(alice, "0xb", features_header="wallet/0")
        self.assertIn("set_admin", result)
        self.assertIn("set_property", result)
        self.assertIn("pledge", result)

    ## Tests: wallet service archive endpoint

    def _call_archive(self, caller, wallet_ident, features_header=None):
        """Call the archive endpoint via the wallet service."""
        mock_request = self._mock_request(caller, features_header=features_header)
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
        self.assertEqual(wallet_bob.comchain_status, "disabled")
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
        self.assertEqual(wallet_bob.comchain_status, "disabled")
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
        self.assertEqual(wallet_bob.comchain_status, "disabled")
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

    ## Tests: wallet service archived endpoint

    def _call_archived(self, caller, features_header=None):
        """Call the archived endpoint via the wallet service."""
        mock_request = self._mock_request(caller, features_header=features_header)
        service = self._get_wallet_service(caller.user)
        with patch.object(svc, "request", mock_request):
            return service.archived()

    def test_ws_archived_returns_archived_idents(self):
        """archived endpoint returns idents of archived wallets."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")
        charly = self._make_user_and_wallet("charly", comchain_type="0", addr="0xc")

        # Archive bob's wallet
        self._call_archive(alice, "0xb", features_header="wallet/0")

        result = self._call_archived(alice, features_header="wallet/0")
        self.assertEqual(result, ["0xb"])

    def test_ws_archived_empty_when_none_archived(self):
        """archived endpoint returns empty list when no wallets are archived."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")

        result = self._call_archived(alice, features_header="wallet/0")
        self.assertEqual(result, [])

    def test_ws_archived_personal_denied(self):
        """Personal user (no actions) is denied on archived endpoint."""
        alice = self._make_user_and_wallet("alice", comchain_type="0", addr="0xa")

        with self.assertRaises(AccessDenied):
            self._call_archived(alice, features_header="wallet/0")

    def test_ws_archived_pledge_allowed(self):
        """Pledge user (has actions) can list archived wallets."""
        alice = self._make_user_and_wallet("alice", comchain_type="3", addr="0xa")

        result = self._call_archived(alice, features_header="wallet/0")
        self.assertEqual(result, [])

    ## Tests: wallet service caller validation

    def test_ws_inactive_caller_denied(self):
        """All wallet service endpoints deny access for inactive caller."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        alice.wallet.active = False

        with self.assertRaises(AccessDenied):
            self._call_update(
                alice, "0xb", {"accountType": 0}, features_header="wallet/0"
            )
        with self.assertRaises(AccessDenied):
            self._call_archive(alice, "0xb", features_header="wallet/0")
        with self.assertRaises(AccessDenied):
            self._call_archived(alice, features_header="wallet/0")

    def test_ws_disabled_caller_denied(self):
        """Wallet service endpoints deny access for disabled caller."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        bob = self._make_user_and_wallet("bob", comchain_type="0", addr="0xb")

        alice.wallet.comchain_status = "disabled"

        with self.assertRaises(AccessDenied):
            self._call_update(
                alice, "0xb", {"accountType": 0}, features_header="wallet/0"
            )
        with self.assertRaises(AccessDenied):
            self._call_archive(alice, "0xb", features_header="wallet/0")
        with self.assertRaises(AccessDenied):
            self._call_archived(alice, features_header="wallet/0")

    def test_ws_cross_currency_denied(self):
        """Wallet on different currency is not found via wallet service."""
        currency_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        other_currency = self.env["res.alt.currency"].create(
            {
                "name": "Other Comchain",
                "ident": "othercc",
                "active": True,
                "engine": "comchain",
                "currency_unit_product_id": currency_product.id,
            }
        )
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        bob = self._make_users("bob")
        self.env["res.partner.backend"].create(
            {
                "partner_id": bob.partner_id.id,
                "name": "comchain:0xb",
                "ident": "0xb",
                "alt_currency_id": other_currency.id,
                "comchain_type": "0",
                "comchain_status": "active",
            }
        )

        # Alice's wallet is on testcomchain, bob's on othercc
        # _resolve_target_wallet searches on alice's currency, won't find bob
        with self.assertRaises(MissingError):
            self._call_update(
                alice, "0xb", {"accountType": 1}, features_header="wallet/0"
            )

    ## Tests: auth_context endpoint (comchain wallet service)

    def _call_auth_context(self, caller, target_ident, features_header=None):
        """Call the comchain auth_context endpoint."""
        mock_request = self._mock_request(caller, features_header=features_header)
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
