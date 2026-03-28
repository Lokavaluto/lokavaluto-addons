from types import SimpleNamespace
from unittest.mock import patch

from minimock import Mock

from odoo.exceptions import AccessDenied
from odoo.tests.common import TransactionCase

import odoo.addons.lcc_lokavaluto_app_connection.services as svc
from odoo.addons.lcc_lokavaluto_app_connection.services import lcc_api


class TestLccApi(TransactionCase):
    """Test the @lcc_api decorator (header, delegation, gating)."""

    def _make_mock_self(self, auth_actions=None):
        """Build a mock service with _auth_user_uri stub."""
        if auth_actions is None:
            auth_actions = []
        return SimpleNamespace(
            env=self.env,
            _auth_user_uri=lambda user_uri: auth_actions,
        )

    def _mock_request(self, headers):
        return Mock(
            "request",
            httprequest=Mock("httprequest", headers=headers),
        )

    def _call_decorated(self, header_value, auth_actions=None, require_actions=None):
        """Call a @lcc_api-decorated dummy with mocked request."""
        result = {}

        @lcc_api([(["/test"], "GET")], require_actions=require_actions)
        def dummy(self):
            result["called"] = True
            return True

        mock_self = self._make_mock_self(auth_actions)
        headers = {}
        if header_value is not None:
            headers["X-Lokapi-Caller-User-Uri"] = header_value
        with patch.object(svc, "request", self._mock_request(headers)):
            dummy(mock_self)

        return result

    ## Tests: header

    def test_missing_header_raises_access_denied(self):
        with self.assertRaises(AccessDenied):
            self._call_decorated(header_value=None)

    def test_empty_header_raises_access_denied(self):
        with self.assertRaises(AccessDenied):
            self._call_decorated(header_value="")

    ## Tests: delegation to _auth_user_uri

    def test_delegates_to_auth_user_uri(self):
        """Decorator passes header value to _auth_user_uri."""
        received = {}

        @lcc_api([(["/test"], "GET")])
        def dummy(self):
            return True

        mock_self = SimpleNamespace(
            env=self.env,
            _auth_user_uri=lambda uri: received.update(uri=uri) or [],
        )
        mock_request = self._mock_request(
            {"X-Lokapi-Caller-User-Uri": "foo://test/user/alice"}
        )
        with patch.object(svc, "request", mock_request):
            dummy(mock_self)

        self.assertEqual(received["uri"], "foo://test/user/alice")

    def test_auth_user_uri_access_denied_propagates(self):
        """AccessDenied from _auth_user_uri propagates."""

        def deny(uri):
            raise AccessDenied()

        mock_self = SimpleNamespace(env=self.env, _auth_user_uri=deny)
        mock_request = self._mock_request(
            {"X-Lokapi-Caller-User-Uri": "foo://test/user/alice"}
        )

        @lcc_api([(["/test"], "GET")])
        def dummy(self):
            return True

        with patch.object(svc, "request", mock_request):
            with self.assertRaises(AccessDenied):
                dummy(mock_self)

    ## Tests: action gating

    def test_require_actions_none_allows_empty(self):
        """require_actions=None: no gating, always passes."""
        result = self._call_decorated(
            header_value="foo://test/user/alice",
            auth_actions=[],
            require_actions=None,
        )
        self.assertTrue(result["called"])

    def test_require_actions_true_rejects_empty(self):
        """require_actions=True: rejects when _auth_user_uri returns []."""
        with self.assertRaises(AccessDenied):
            self._call_decorated(
                header_value="foo://test/user/alice",
                auth_actions=[],
                require_actions=True,
            )

    def test_require_actions_true_accepts_nonempty(self):
        """require_actions=True: passes when actions exist."""
        result = self._call_decorated(
            header_value="foo://test/user/alice",
            auth_actions=["activate"],
            require_actions=True,
        )
        self.assertTrue(result["called"])

    def test_require_actions_tuple_rejects_no_match(self):
        """require_actions=("activate",): rejects when no overlap."""
        with self.assertRaises(AccessDenied):
            self._call_decorated(
                header_value="foo://test/user/alice",
                auth_actions=["search-all-recipients"],
                require_actions=("activate",),
            )

    def test_require_actions_tuple_accepts_match(self):
        """require_actions=("activate",): passes when overlap."""
        result = self._call_decorated(
            header_value="foo://test/user/alice",
            auth_actions=["activate", "search-all-recipients"],
            require_actions=("activate",),
        )
        self.assertTrue(result["called"])
