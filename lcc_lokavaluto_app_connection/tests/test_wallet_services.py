from unittest.mock import patch

from minimock import Mock

from odoo.exceptions import AccessDenied
from odoo.tests.common import TransactionCase

import odoo.addons.lcc_lokavaluto_app_connection.services as svc
from odoo.addons.lcc_lokavaluto_app_connection.services import lcc_api


class TestWalletServiceBase(TransactionCase):
    """Test base WalletService."""

    def _get_wallet_service(self):
        collection = self.env["lokavaluto.private.services"].browse(1)
        with collection.work_on("res.partner.backend") as work:
            return work.component(usage="wallet")

    def _call_with_mock_request(self, endpoint, headers=None):
        mock_request = Mock(
            "request",
            httprequest=Mock("httprequest", headers=headers or {}),
        )
        with patch.object(svc, "request", mock_request):
            return endpoint()

    def test_auth_user_uri_returns_empty_actions(self):
        """Base _auth_user_uri returns empty list (no-op)."""
        service = self._get_wallet_service()
        result = service._auth_user_uri("foo://test/user/alice")
        self.assertEqual(result, [])

    def test_lcc_api_with_base_auth_passes_without_gate(self):
        """@lcc_api with require_actions=None passes with base no-op auth."""
        service = self._get_wallet_service()
        result = {}

        @lcc_api([(["/test"], "GET")])
        def dummy(self):
            result["called"] = True
            return True

        self._call_with_mock_request(
            lambda: dummy(service),
            headers={"X-Lokapi-Caller-User-Uri": "foo://test/user/alice"},
        )
        self.assertTrue(result["called"])

    def test_lcc_api_with_base_auth_rejects_with_gate(self):
        """@lcc_api with an admin gate rejects when base returns []."""
        from odoo.addons.lcc_lokavaluto_app_connection.services.gate import (
            ANY_ADMIN_ACTION,
        )

        service = self._get_wallet_service()

        @lcc_api([(["/test"], "GET")], require_actions=ANY_ADMIN_ACTION)
        def dummy(self):
            return True

        with self.assertRaises(AccessDenied):
            self._call_with_mock_request(
                lambda: dummy(service),
                headers={"X-Lokapi-Caller-User-Uri": "foo://test/user/alice"},
            )
