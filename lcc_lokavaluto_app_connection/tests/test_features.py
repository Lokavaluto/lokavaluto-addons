from types import SimpleNamespace
from unittest.mock import patch

from minimock import Mock

from odoo.tests.common import TransactionCase

import odoo.addons.lcc_lokavaluto_app_connection.services as svc
from odoo.addons.lcc_lokavaluto_app_connection.services import (
    MissingCommonFeature,
    _features_restapi_method,
    features,
    features_header_parse,
)


class TestFeaturesHeaderParse(TransactionCase):
    """Test features_header_parse utility."""

    def test_single_version(self):
        result = list(features_header_parse("search/1"))
        self.assertEqual(result, ["search/1"])

    def test_version_range(self):
        result = list(features_header_parse("search/0-2"))
        self.assertEqual(result, ["search/0", "search/1", "search/2"])

    def test_comma_separated(self):
        result = list(features_header_parse("cap/0-2,5"))
        self.assertEqual(result, ["cap/0", "cap/1", "cap/2", "cap/5"])

    def test_multiple_features(self):
        result = list(features_header_parse("search/0-1 auth/2"))
        self.assertEqual(result, ["search/0", "search/1", "auth/2"])

    def test_featureless(self):
        result = list(features_header_parse("feature-less/0"))
        self.assertEqual(result, ["feature-less/0"])


class TestFeaturesDecorator(TransactionCase):
    """Test @features decorator and helper functions."""

    def _mock_request(self, headers):
        """Helper to build a mock request with given headers."""

        return Mock(
            "request",
            httprequest=Mock("httprequest", headers=headers or {}),
            future_response=Mock("future_response", headers={}),
            _common_features=None,
        )

    def _call_with_mock_request(self, endpoint, headers=None):
        """Call endpoint with mocked request headers.

        Returns whatever the endpoint stored in its closure.
        """
        mock_request = self._mock_request(headers)
        with patch.object(svc, "request", mock_request):
            endpoint(SimpleNamespace())
        return mock_request

    def test_no_header_legacy_client_rejected(self):
        """Legacy client (no header) rejected by endpoint requiring features."""

        @features("search/1")
        def dummy(self):
            pass

        mock_request = self._mock_request(headers={})
        with patch.object(svc, "request", mock_request):
            with self.assertRaises(MissingCommonFeature):
                dummy(SimpleNamespace())
        self.assertEqual(
            mock_request.future_response.headers["X-Supported-Features"],
            "search/1",
        )

    def test_no_header_explicit_featureless_allowed(self):
        """Endpoint explicitly declaring feature-less/0 allows legacy clients."""
        result = {}

        @features("search/1 feature-less/0")
        def dummy(self):
            result["common"] = svc.request._common_features.copy()

        mock_req = self._call_with_mock_request(dummy)
        self.assertIn("feature-less/0", result["common"])
        self.assertEqual(
            mock_req.future_response.headers["X-Supported-Features"],
            "feature-less/0 search/1",
        )

    def test_no_header_no_features_declared_allowed(self):
        """Legacy client + no features declared → allowed via feature-less/0."""

        @features("")
        def dummy(self):
            pass

        mock_req = self._call_with_mock_request(dummy)
        self.assertNotIn("X-Selected-Features", mock_req.future_response.headers)

    def test_matching_feature_negotiated(self):
        result = {}

        @features("search/1-2")
        def dummy(self):
            result["common"] = svc.request._common_features.copy()

        self._call_with_mock_request(dummy, headers={"X-Client-Features": "search/2"})
        self.assertIn("search/2", result["common"])

    def test_no_common_feature_raises(self):
        @features("auth/3")
        def dummy(self):
            pass

        with self.assertRaises(MissingCommonFeature):
            self._call_with_mock_request(
                dummy, headers={"X-Client-Features": "search/1"}
            )

    def test_with_feature_marks_used(self):
        result = {}

        @features("search/1-2")
        def dummy(self):
            result["used_1"] = svc.with_feature("search/1")
            result["used_3"] = svc.with_feature("search/3")
            result["used_features"] = svc.request._used_features.copy()

        self._call_with_mock_request(dummy, headers={"X-Client-Features": "search/1-2"})
        self.assertTrue(result["used_1"])
        self.assertFalse(result["used_3"])
        self.assertEqual(result["used_features"], {"search/1"})

    def test_has_feature_without_marking(self):
        result = {}

        @features("search/1")
        def dummy(self):
            result["has"] = svc.has_feature("search/1")
            result["used"] = svc.request._used_features.copy()

        self._call_with_mock_request(dummy, headers={"X-Client-Features": "search/1"})
        self.assertTrue(result["has"])
        self.assertEqual(result["used"], set())

    def test_used_features_set_response_header(self):
        """Used features appear in X-Selected-Features response header."""

        @features("search/1-2 auth/1")
        def dummy(self):
            svc.with_feature("search/2")
            svc.with_feature("auth/1")

        mock_req = self._call_with_mock_request(
            dummy, headers={"X-Client-Features": "search/1-2 auth/1"}
        )
        self.assertEqual(
            mock_req.future_response.headers["X-Selected-Features"],
            "auth/1 search/2",
        )

    def test_no_used_features_one_real_auto_selects(self):
        """One real common feature auto-selected when nothing used."""

        @features("search/1")
        def dummy(self):
            pass

        mock_req = self._call_with_mock_request(
            dummy, headers={"X-Client-Features": "search/1"}
        )
        self.assertEqual(
            mock_req.future_response.headers["X-Selected-Features"],
            "search/1",
        )

    def test_no_used_features_multiple_real_raises(self):
        """Multiple real common features without use_feature raises."""

        @features("wallet/0-2")
        def dummy(self):
            pass

        with self.assertRaises(ValueError):
            self._call_with_mock_request(
                dummy, headers={"X-Client-Features": "wallet/1-2"}
            )

    def test_use_feature_not_negotiated_raises(self):
        """use_feature raises ValueError if feature was not negotiated."""

        @features("search/1")
        def dummy(self):
            svc.use_feature("auth/1")

        with self.assertRaises(ValueError):
            self._call_with_mock_request(
                dummy, headers={"X-Client-Features": "search/1"}
            )

    ## Tests: stacked @features

    def test_stacked_features_union(self):
        """Stacked @features accumulate supported sets (union)."""

        @features("wallet/0")
        @features("search/1")
        def dummy(self):
            svc.use_feature("search/1")

        mock_req = self._call_with_mock_request(
            dummy, headers={"X-Client-Features": "search/1"}
        )
        self.assertEqual(
            mock_req.future_response.headers["X-Selected-Features"],
            "search/1",
        )
        self.assertEqual(
            mock_req.future_response.headers["X-Supported-Features"],
            "search/1 wallet/0",
        )

    def test_stacked_features_union_2(self):
        """Stacked @features accumulate supported sets (union)."""

        @features("wallet/0")
        @features("search/1")
        def dummy(self):
            svc.use_feature("wallet/0")

        mock_req = self._call_with_mock_request(
            dummy, headers={"X-Client-Features": "wallet/0"}
        )
        self.assertEqual(
            mock_req.future_response.headers["X-Selected-Features"],
            "wallet/0",
        )

    def test_stacked_features_no_common_raises(self):
        """Stacked features — client supports neither → rejected."""

        @features("wallet/0")
        @features("search/1")
        def dummy(self):
            pass

        with self.assertRaises(MissingCommonFeature):
            self._call_with_mock_request(dummy, headers={"X-Client-Features": "auth/1"})

    def test_stacked_features_multiple_common_requires_use_feature(self):
        """Stacked features — multiple common, must call use_feature."""

        @features("wallet/0")
        @features("search/1")
        def dummy(self):
            pass

        with self.assertRaises(ValueError):
            self._call_with_mock_request(
                dummy,
                headers={"X-Client-Features": "wallet/0 search/1"},
            )

    def test_stacked_features_one_common_auto_selects(self):
        """Stacked features — one common, auto-selected."""

        @features("wallet/0")
        @features("search/1")
        def dummy(self):
            pass

        mock_req = self._call_with_mock_request(
            dummy,
            headers={"X-Client-Features": "wallet/0"},
        )
        self.assertEqual(
            mock_req.future_response.headers["X-Selected-Features"],
            "wallet/0",
        )


class TestRestapiMethodAutoWrap(TransactionCase):
    """Test that the restapi.method monkey-patch auto-wraps with features."""

    def _passthrough_restapi_method(self, received):
        """Return a mock restapi.method that records what it receives."""

        def mock_method(routes, **kwargs):
            def decorator(func):
                received["func"] = func
                received["routes"] = routes
                return func

            return decorator

        return mock_method

    def test_auto_wraps_bare_function(self):
        """Function without @features gets auto-wrapped with features("")."""
        received = {}

        def dummy(self):
            pass

        with patch.object(
            svc, "_orig_restapi_method", self._passthrough_restapi_method(received)
        ):
            _features_restapi_method([(["/test"], "GET")])(dummy)

        wrapped = received["func"]
        self.assertEqual(wrapped._supported_features, set())

    def test_preserves_explicit_features(self):
        """Function with explicit @features is NOT re-wrapped."""
        received = {}

        @features("wallet/0")
        def dummy(self):
            pass

        original = dummy

        with patch.object(
            svc, "_orig_restapi_method", self._passthrough_restapi_method(received)
        ):
            _features_restapi_method([(["/test"], "GET")])(dummy)

        self.assertIs(received["func"], original)
        self.assertEqual(received["func"]._supported_features, {"wallet/0"})
