from unittest.mock import patch

from odoo.exceptions import AccessDenied
from odoo.addons.lcc_lokavaluto_app_connection.datamodel.partner_info import (
    PartnerSearchInfo,
)

import odoo.addons.lcc_lokavaluto_app_connection.services as svc

from .common import ComchainTestCase


class TestRecipientServiceSearchAll(ComchainTestCase):
    ## Helpers

    def _call_search_all(self, caller, value="", features_header=None):
        mock_request = self._mock_request(caller, features_header=features_header)
        service = self._get_recipient_service(caller.user)
        backend_keys = [
            f"{self.comchain_currency.engine}:{self.comchain_currency.ident}"
        ]
        params = PartnerSearchInfo(
            value=value,
            backend_keys=backend_keys,
            offset=0,
            limit=30,
            order="name asc",
        )
        with patch.object(svc, "request", mock_request):
            return service.search_all(params)

    ## Tests

    def test_admin_can_search_all(self):
        """Admin (type 2) can search all recipients."""
        alice = self._make_user_and_wallet("alice", comchain_type="2", addr="0xa")
        bob = self._make_user_and_wallet("bob", addr="0xb")

        result = self._call_search_all(
            alice, value="bob", features_header="recipient/0"
        )
        self.assertGreater(result["count"], 0)

    def test_property_admin_can_search_all(self):
        """Property admin (type 4) can search all recipients."""
        alice = self._make_user_and_wallet("alice", comchain_type="4", addr="0xa")
        bob = self._make_user_and_wallet("bob", addr="0xb")

        result = self._call_search_all(
            alice, value="bob", features_header="recipient/0"
        )
        self.assertGreater(result["count"], 0)

    def test_admin_sees_self_in_results(self):
        """Unlike search_recipients, search_all includes the caller."""
        charlie = self._make_user_and_wallet("charlie", comchain_type="2", addr="0xa")

        result = self._call_search_all(
            charlie, value="charlie", features_header="recipient/0"
        )
        result_ids = {row["id"] for row in result["rows"]}
        self.assertIn(charlie.user.partner_id.id, result_ids)

    def test_personal_user_denied(self):
        """Personal user (type 0, no search-all-recipients action) is denied."""
        alice = self._make_user_and_wallet("alice", comchain_type="0", addr="0xa")

        with self.assertRaises(AccessDenied):
            self._call_search_all(
                alice, value="whatever", features_header="recipient/0"
            )

    def test_pledge_user_denied(self):
        """Pledge user (type 3, no search-all-recipients action) is denied."""
        alice = self._make_user_and_wallet("alice", comchain_type="3", addr="0xa")

        with self.assertRaises(AccessDenied):
            self._call_search_all(
                alice, value="whatever", features_header="recipient/0"
            )

    def test_search_all_ignores_restriction_rules(self):
        """Wallet restriction rules must NOT filter search_all results."""
        charlie = self._make_user_and_wallet("charlie", comchain_type="2", addr="0xa")
        alice = self._make_user_and_wallet("alice", addr="0xb")
        bob = self._make_user_and_wallet("bob", addr="0xc")

        # Restriction rule only allows bob as recipient for charlie
        self.env["wallet.restriction.rule"].create(
            {
                "name": "Restrictive Rule",
                "active": True,
                "sender_wallet_domain": "[('name', '=', 'comchain:0xa')]",
                "recipient_wallet_domain": "[('name', '=', 'comchain:0xc')]",
            }
        )

        # search_all should ignore restriction rules — both alice and bob visible
        # (non-empty value needed to trigger full search; empty returns favorites only)
        # Search for alice specifically — she would be blocked by the rule
        # in search_recipients but should appear in search_all
        result = self._call_search_all(
            charlie, value="alice", features_header="recipient/0"
        )
        result_ids = {row["id"] for row in result["rows"]}
        self.assertIn(alice.user.partner_id.id, result_ids)
