from types import SimpleNamespace
from unittest.mock import patch

from minimock import Mock

from odoo.exceptions import AccessDenied
from odoo.tests.common import TransactionCase

import odoo.addons.lcc_lokavaluto_app_connection.services as svc
from odoo.addons.lcc_lokavaluto_app_connection.services import (
    _parse_caller_ident,
    lcc_api,
)
from odoo.addons.lcc_lokavaluto_app_connection.services.gate import (
    ANY_ADMIN_ACTION,
    SELF,
    And,
    GateContext,
    GateExpr,
    GateLit,
    GateOp,
    Not,
    Or,
    Self,
)


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

    def _call_decorated(
        self,
        header_value,
        auth_actions=None,
        require_actions=None,
        target_ident=None,
    ):
        """Call a @lcc_api-decorated dummy with mocked request.

        If *target_ident* is given, the dummy takes a ``wallet_ident``
        kwarg; otherwise it is targetless.
        """
        result = {}

        if target_ident is None:

            @lcc_api([(["/test"], "GET")], require_actions=require_actions)
            def dummy(self):
                result["called"] = True
                return True

            call = lambda: dummy(self._make_mock_self(auth_actions))
        else:

            @lcc_api([(["/test"], "GET")], require_actions=require_actions)
            def dummy(self, wallet_ident):
                result["called"] = True
                return True

            call = lambda: dummy(
                self._make_mock_self(auth_actions),
                wallet_ident=target_ident,
            )

        headers = {}
        if header_value is not None:
            headers["X-Lokapi-Caller-User-Uri"] = header_value
        with patch.object(svc, "request", self._mock_request(headers)):
            call()

        return result

    ## Tests: header

    def test_missing_header_raises_access_denied(self):
        with self.assertRaises(AccessDenied):
            self._call_decorated(header_value=None)

    def test_empty_header_raises_access_denied(self):
        with self.assertRaises(AccessDenied):
            self._call_decorated(header_value="")

    def test_malformed_uri_raises_access_denied_before_delegation(self):
        """A malformed URI fails early: no ``_auth_user_uri`` call.

        The decorator must reject the request at parse time — before
        delegating to the backend auth hook — so malformed inputs
        never reach backend-specific code and are logged uniformly.
        """
        call_log = []

        @lcc_api([(["/test"], "GET")])
        def dummy(self):
            return True

        mock_self = SimpleNamespace(
            env=self.env,
            _auth_user_uri=lambda uri: call_log.append(uri) or [],
        )
        mock_request = self._mock_request(
            {"X-Lokapi-Caller-User-Uri": "garbage-no-user-segment"}
        )
        with patch.object(svc, "request", mock_request):
            with self.assertRaises(AccessDenied):
                dummy(mock_self)

        ## _auth_user_uri must NOT have been called.
        self.assertEqual(call_log, [])

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

    ## Tests: gate DSL via the decorator

    def test_require_actions_none_allows_empty(self):
        """require_actions=None: no gate, any caller passes."""
        result = self._call_decorated(
            header_value="foo://test/user/alice",
            auth_actions=[],
            require_actions=None,
        )
        self.assertTrue(result["called"])

    def test_require_actions_none_allows_any_actions(self):
        """require_actions=None: passes even with actions present."""
        result = self._call_decorated(
            header_value="foo://test/user/alice",
            auth_actions=["activate", "reconvert"],
            require_actions=None,
        )
        self.assertTrue(result["called"])

    def test_require_actions_string_shorthand_accepts(self):
        """A bare string is auto-wrapped: matches when caller has it."""
        result = self._call_decorated(
            header_value="foo://test/user/alice",
            auth_actions=["activate"],
            require_actions="activate",
        )
        self.assertTrue(result["called"])

    def test_require_actions_string_shorthand_rejects(self):
        """A bare string rejects when the caller lacks the action."""
        with self.assertRaises(AccessDenied):
            self._call_decorated(
                header_value="foo://test/user/alice",
                auth_actions=["reconvert"],
                require_actions="activate",
            )

    def test_require_actions_or_accepts_any_overlap(self):
        """Or passes when caller holds at least one listed action."""
        result = self._call_decorated(
            header_value="foo://test/user/alice",
            auth_actions=["search-all-recipients"],
            require_actions=Or("activate", "search-all-recipients"),
        )
        self.assertTrue(result["called"])

    def test_require_actions_or_rejects_no_overlap(self):
        """Or rejects when no listed action is held."""
        with self.assertRaises(AccessDenied):
            self._call_decorated(
                header_value="foo://test/user/alice",
                auth_actions=["reconvert"],
                require_actions=Or("activate", "search-all-recipients"),
            )

    def test_require_actions_or_rejects_empty_caller(self):
        """Or rejects a caller with no actions."""
        with self.assertRaises(AccessDenied):
            self._call_decorated(
                header_value="foo://test/user/alice",
                auth_actions=[],
                require_actions=Or("activate"),
            )

    def test_require_actions_and_accepts_full_match(self):
        """And passes only when caller has every listed action."""
        result = self._call_decorated(
            header_value="foo://test/user/alice",
            auth_actions=["activate", "search-all-recipients"],
            require_actions=And("activate", "search-all-recipients"),
        )
        self.assertTrue(result["called"])

    def test_require_actions_and_rejects_partial_match(self):
        """And rejects when one of the required actions is missing."""
        with self.assertRaises(AccessDenied):
            self._call_decorated(
                header_value="foo://test/user/alice",
                auth_actions=["activate"],
                require_actions=And("activate", "search-all-recipients"),
            )

    def test_require_actions_not_inverts(self):
        """Not(expr) passes when expr rejects and vice versa."""
        with self.assertRaises(AccessDenied):
            self._call_decorated(
                header_value="foo://test/user/alice",
                auth_actions=["reconvert"],
                require_actions=Not("reconvert"),
            )
        result = self._call_decorated(
            header_value="foo://test/user/alice",
            auth_actions=["activate"],
            require_actions=Not("reconvert"),
        )
        self.assertTrue(result["called"])

    def test_require_actions_nested_combinator(self):
        """And nested inside Not (De Morgan-style compositions work)."""
        result = self._call_decorated(
            header_value="foo://test/user/alice",
            auth_actions=["activate"],
            require_actions=Not(And("activate", "reconvert")),
        )
        self.assertTrue(result["called"])
        with self.assertRaises(AccessDenied):
            self._call_decorated(
                header_value="foo://test/user/alice",
                auth_actions=["activate", "reconvert"],
                require_actions=Not(And("activate", "reconvert")),
            )

    def test_require_actions_legacy_true_raises_type_error(self):
        """Legacy ``True`` is no longer accepted."""
        with self.assertRaises(TypeError):
            self._call_decorated(
                header_value="foo://test/user/alice",
                auth_actions=["activate"],
                require_actions=True,
            )

    def test_require_actions_legacy_tuple_raises_type_error(self):
        """Legacy tuple form is no longer accepted."""
        with self.assertRaises(TypeError):
            self._call_decorated(
                header_value="foo://test/user/alice",
                auth_actions=["activate"],
                require_actions=("activate",),
            )

    ## Tests: SELF gate via decorator

    def test_self_matches_when_ident_equals_target(self):
        """``SELF`` passes when caller and target idents match."""
        result = self._call_decorated(
            header_value="foo://test/user/alice",
            auth_actions=[],
            require_actions=SELF,
            target_ident="alice",
        )
        self.assertTrue(result["called"])

    def test_self_rejects_when_ident_differs(self):
        """``SELF`` rejects when caller and target idents differ."""
        with self.assertRaises(AccessDenied):
            self._call_decorated(
                header_value="foo://test/user/alice",
                auth_actions=[],
                require_actions=SELF,
                target_ident="bob",
            )

    def test_self_or_admin_accepts_self(self):
        """``SELF | ANY_ADMIN_ACTION`` accepts self-match."""
        result = self._call_decorated(
            header_value="foo://test/user/alice",
            auth_actions=[],
            require_actions=SELF | ANY_ADMIN_ACTION,
            target_ident="alice",
        )
        self.assertTrue(result["called"])

    def test_self_or_admin_accepts_admin_on_other(self):
        """``SELF | ANY_ADMIN_ACTION`` accepts admin targeting another."""
        result = self._call_decorated(
            header_value="foo://test/user/alice",
            auth_actions=["activate"],
            require_actions=SELF | ANY_ADMIN_ACTION,
            target_ident="bob",
        )
        self.assertTrue(result["called"])

    def test_self_or_admin_rejects_personal_on_other(self):
        """``SELF | ANY_ADMIN_ACTION`` rejects personal caller on other."""
        with self.assertRaises(AccessDenied):
            self._call_decorated(
                header_value="foo://test/user/alice",
                auth_actions=[],
                require_actions=SELF | ANY_ADMIN_ACTION,
                target_ident="bob",
            )

    def test_self_or_admin_rejects_reconvert_alone_on_other(self):
        """CRITICAL: reconvert alone does NOT grant admin access on other."""
        with self.assertRaises(AccessDenied):
            self._call_decorated(
                header_value="foo://test/user/alice",
                auth_actions=["reconvert"],
                require_actions=SELF | ANY_ADMIN_ACTION,
                target_ident="bob",
            )

    def test_self_on_targetless_endpoint_raises_typeerror(self):
        """Using ``SELF`` on a targetless endpoint is a decoration-time error."""
        with self.assertRaises(TypeError):

            @lcc_api([(["/test"], "GET")], require_actions=SELF)
            def dummy(self):
                return True

    def test_self_inside_or_on_targetless_endpoint_raises_typeerror(self):
        """``SELF`` nested in Or on targetless endpoint is still caught."""
        with self.assertRaises(TypeError):

            @lcc_api(
                [(["/test"], "GET")],
                require_actions=SELF | ANY_ADMIN_ACTION,
            )
            def dummy(self):
                return True

    def test_self_with_target_does_not_raise_at_decoration(self):
        """``SELF`` on an endpoint that accepts wallet_ident is valid."""

        @lcc_api([(["/<wallet_ident>/x"], "GET")], require_actions=SELF)
        def dummy(self, wallet_ident):
            return "ok"

        self.assertTrue(callable(dummy))


class TestParseCallerIdent(TransactionCase):
    """Unit tests for _parse_caller_ident (fail-early on malformed URIs)."""

    def test_parse_simple_uri(self):
        self.assertEqual(
            _parse_caller_ident("comchain://Lemanopolis/user/0xabc"),
            "0xabc",
        )

    def test_parse_foo_scheme(self):
        self.assertEqual(
            _parse_caller_ident("foo://testcc/user/alice"),
            "alice",
        )

    def test_parse_unquotes(self):
        """URL-encoded idents are normalised."""
        self.assertEqual(
            _parse_caller_ident("foo://testcc/user/hello%20world"),
            "hello world",
        )

    def test_parse_malformed_no_user_segment(self):
        """URI without a ``/user/`` path segment raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            _parse_caller_ident("foo://testcc/wallet/alice")
        self.assertIn("foo://testcc/wallet/alice", str(cm.exception))

    def test_parse_malformed_no_path(self):
        """URI without any path raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            _parse_caller_ident("foo://testcc")
        self.assertIn("foo://testcc", str(cm.exception))

    def test_parse_malformed_missing_ident(self):
        """URI with ``/user/`` but empty ident raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            _parse_caller_ident("foo://testcc/user/")
        self.assertIn("foo://testcc/user/", str(cm.exception))

    def test_parse_malformed_garbage(self):
        """Entirely non-URI input raises ValueError."""
        with self.assertRaises(ValueError):
            _parse_caller_ident("not a uri at all")


class TestGateDslUnit(TransactionCase):
    """Unit tests for the gate DSL classes themselves."""

    def _ctx(self, caller_actions=(), caller_ident=None, target_ident=None):
        return GateContext(
            caller_actions=frozenset(caller_actions),
            caller_wallet_ident=caller_ident,
            target_wallet_ident=target_ident,
        )

    ## GateLit — leaf holding a single action string

    def test_gatelit_matches_when_caller_has_action(self):
        self.assertTrue(
            GateLit("activate").matches(self._ctx(caller_actions=["activate"]))
        )

    def test_gatelit_rejects_when_caller_lacks_action(self):
        self.assertFalse(
            GateLit("activate").matches(self._ctx(caller_actions=["other"]))
        )

    def test_gatelit_rejects_empty_caller(self):
        self.assertFalse(GateLit("activate").matches(self._ctx()))

    def test_gatelit_rejects_non_string_action(self):
        """GateLit requires a str."""
        with self.assertRaises(TypeError):
            GateLit(42)
        with self.assertRaises(TypeError):
            GateLit(None)
        with self.assertRaises(TypeError):
            GateLit(["a"])

    def test_gatelit_is_gate_expr_not_gate_op(self):
        """GateLit is a leaf expression, not an operation."""
        lit = GateLit("a")
        self.assertIsInstance(lit, GateExpr)
        self.assertNotIsInstance(lit, GateOp)

    def test_gatelit_needs_target_default_false(self):
        self.assertFalse(GateLit("a").needs_target)

    ## Or — variadic; auto-wraps strings to GateLit

    def test_or_empty_never_matches(self):
        self.assertFalse(Or().matches(self._ctx()))
        self.assertFalse(Or().matches(self._ctx(caller_actions=["activate"])))

    def test_or_matches_overlap(self):
        self.assertTrue(Or("a", "b").matches(self._ctx(caller_actions=["b", "c"])))

    def test_or_no_overlap(self):
        self.assertFalse(Or("a", "b").matches(self._ctx(caller_actions=["c"])))

    def test_or_accepts_mixed_strings_and_expressions(self):
        """Strings auto-wrap; expressions pass through unchanged."""
        expr = Or("a", SELF)
        ## Caller has 'a' → matches
        self.assertTrue(expr.matches(self._ctx(caller_actions=["a"])))
        ## Caller is self on the target → matches
        self.assertTrue(
            expr.matches(self._ctx(caller_ident="alice", target_ident="alice"))
        )
        ## Neither branch → rejects
        self.assertFalse(
            expr.matches(self._ctx(caller_ident="alice", target_ident="bob"))
        )

    def test_or_rejects_non_string_non_expr_operand(self):
        """Or operands must be GateExpr or str."""
        with self.assertRaises(TypeError):
            Or(42)
        with self.assertRaises(TypeError):
            Or("a", None)
        with self.assertRaises(TypeError):
            Or(["a"])  # list is not str or GateExpr

    ## And — variadic

    def test_and_empty_always_matches(self):
        """Vacuous truth for empty And."""
        self.assertTrue(And().matches(self._ctx()))
        self.assertTrue(And().matches(self._ctx(caller_actions=["x"])))

    def test_and_full_match(self):
        self.assertTrue(
            And("a", "b").matches(self._ctx(caller_actions=["a", "b", "c"]))
        )

    def test_and_partial_rejects(self):
        self.assertFalse(And("a", "b").matches(self._ctx(caller_actions=["a"])))

    def test_and_rejects_non_string_non_expr_operand(self):
        with self.assertRaises(TypeError):
            And(42)
        with self.assertRaises(TypeError):
            And("a", False)

    ## Not — arity 1, accepts GateExpr or str (auto-wrap)

    def test_not_inverts_lit(self):
        expr = Not("a")
        self.assertTrue(expr.matches(self._ctx()))
        self.assertFalse(expr.matches(self._ctx(caller_actions=["a"])))

    def test_not_inverts_and(self):
        expr = Not(And("a", "b"))
        self.assertTrue(expr.matches(self._ctx(caller_actions=["a"])))
        self.assertFalse(expr.matches(self._ctx(caller_actions=["a", "b"])))

    def test_not_rejects_wrong_arity_zero(self):
        with self.assertRaises(TypeError):
            Not()

    def test_not_rejects_wrong_arity_many(self):
        with self.assertRaises(TypeError):
            Not("a", "b")

    def test_not_rejects_non_expr_non_str(self):
        with self.assertRaises(TypeError):
            Not(42)

    ## Self — arity 0, no operands

    def test_self_rejects_any_operand(self):
        with self.assertRaises(TypeError):
            Self("alice")
        with self.assertRaises(TypeError):
            Self(Or("a"))

    def test_self_matches_equal_idents(self):
        self.assertTrue(
            Self().matches(self._ctx(caller_ident="alice", target_ident="alice"))
        )

    def test_self_rejects_different_idents(self):
        self.assertFalse(
            Self().matches(self._ctx(caller_ident="alice", target_ident="bob"))
        )

    def test_self_rejects_no_caller_ident(self):
        self.assertFalse(
            Self().matches(self._ctx(caller_ident=None, target_ident="alice"))
        )

    def test_self_rejects_no_target_ident(self):
        self.assertFalse(
            Self().matches(self._ctx(caller_ident="alice", target_ident=None))
        )

    def test_self_rejects_both_none(self):
        self.assertFalse(Self().matches(self._ctx()))

    def test_self_needs_target(self):
        self.assertTrue(Self().needs_target)
        self.assertFalse(Or("a").needs_target)
        self.assertFalse(And("a").needs_target)
        self.assertFalse(Not("a").needs_target)
        self.assertFalse(GateLit("a").needs_target)

    def test_self_needs_target_propagates_through_or(self):
        self.assertTrue((SELF | "activate").needs_target)

    def test_self_needs_target_propagates_through_and(self):
        self.assertTrue((SELF & "activate").needs_target)

    def test_self_needs_target_propagates_through_not(self):
        self.assertTrue(Not(SELF).needs_target)

    ## SELF singleton

    def test_self_singleton_is_instance_of_self(self):
        """``SELF`` is a pre-built instance of :class:`Self`."""
        self.assertIsInstance(SELF, Self)

    def test_self_singleton_behaves_like_self(self):
        """``SELF`` matches and reprs identically to ``Self()``."""
        ctx_match = self._ctx(caller_ident="alice", target_ident="alice")
        ctx_diff = self._ctx(caller_ident="alice", target_ident="bob")
        self.assertTrue(SELF.matches(ctx_match))
        self.assertFalse(SELF.matches(ctx_diff))
        self.assertTrue(SELF.needs_target)
        self.assertEqual(repr(SELF), "Self()")

    def test_self_singleton_composes_with_operators(self):
        """``SELF | <...>`` is a valid gate expression."""
        expr = SELF | "activate"
        self.assertTrue(expr.needs_target)
        ## Self branch
        self.assertTrue(expr.matches(self._ctx(caller_ident="a", target_ident="a")))
        ## Action branch
        self.assertTrue(
            expr.matches(
                self._ctx(
                    caller_actions=["activate"],
                    caller_ident="a",
                    target_ident="b",
                )
            )
        )
        ## Neither branch
        self.assertFalse(expr.matches(self._ctx(caller_ident="a", target_ident="b")))

    ## Operator sugar

    def test_or_operator(self):
        expr = GateLit("a") | GateLit("b")
        self.assertIsInstance(expr, Or)
        self.assertTrue(expr.matches(self._ctx(caller_actions=["a"])))
        self.assertTrue(expr.matches(self._ctx(caller_actions=["b"])))
        self.assertFalse(expr.matches(self._ctx(caller_actions=["c"])))

    def test_or_operator_auto_wraps_strings(self):
        """``expr | 'str'`` auto-wraps via GateOp.__init__."""
        expr = SELF | "activate"
        self.assertIsInstance(expr, Or)
        ## The string operand is stored as a GateLit.
        self.assertIsInstance(expr._operands[1], GateLit)

    def test_or_operator_is_left_associative(self):
        """``a | b | c`` nests as ``Or(Or(a, b), c)`` (no flattening)."""
        expr = GateLit("a") | GateLit("b") | GateLit("c")
        self.assertIsInstance(expr, Or)
        self.assertEqual(len(expr._operands), 2)
        self.assertIsInstance(expr._operands[0], Or)
        self.assertIsInstance(expr._operands[1], GateLit)

    def test_and_operator(self):
        expr = GateLit("a") & GateLit("b")
        self.assertIsInstance(expr, And)
        self.assertTrue(expr.matches(self._ctx(caller_actions=["a", "b"])))
        self.assertFalse(expr.matches(self._ctx(caller_actions=["a"])))

    def test_invert_operator(self):
        expr = ~GateLit("a")
        self.assertIsInstance(expr, Not)
        self.assertTrue(expr.matches(self._ctx()))
        self.assertFalse(expr.matches(self._ctx(caller_actions=["a"])))

    def test_operator_accepts_string_shorthand_via_rop(self):
        ## "a" | GateLit("b") routes through __ror__; the string is
        ## auto-wrapped by Or's constructor.
        expr = "a" | GateLit("b")
        self.assertTrue(expr.matches(self._ctx(caller_actions=["a"])))

    ## __repr__ (source-like rendering)

    def test_repr_gatelit(self):
        self.assertEqual(repr(GateLit("activate")), "'activate'")

    def test_repr_or_preserves_order(self):
        self.assertEqual(repr(Or("b", "a")), "Or('b', 'a')")
        self.assertEqual(repr(Or("a", "b")), "Or('a', 'b')")

    def test_repr_or_empty(self):
        self.assertEqual(repr(Or()), "Or()")

    def test_repr_and_preserves_order(self):
        self.assertEqual(repr(And("b", "a")), "And('b', 'a')")
        self.assertEqual(repr(And("a", "b")), "And('a', 'b')")

    def test_repr_and_empty(self):
        self.assertEqual(repr(And()), "And()")

    def test_repr_not(self):
        self.assertEqual(repr(Not("a")), "Not('a')")

    def test_repr_self(self):
        self.assertEqual(repr(Self()), "Self()")

    def test_repr_or_combined_via_operator(self):
        """``Or('a') | Or('b')`` nests (no flattening) \u2192 ``Or(Or('a'), Or('b'))``."""
        self.assertEqual(
            repr(Or("a") | Or("b")),
            "Or(Or('a'), Or('b'))",
        )

    def test_repr_and_combined_via_operator(self):
        """``And('a') & And('b')`` nests \u2192 ``And(And('a'), And('b'))``."""
        self.assertEqual(
            repr(And("a") & And("b")),
            "And(And('a'), And('b'))",
        )

    def test_repr_self_or_admin(self):
        """``SELF | ANY_ADMIN_ACTION`` nests the admin ``Or``."""
        self.assertEqual(
            repr(SELF | ANY_ADMIN_ACTION),
            "Or(Self(), Or('activate', 'search-all-recipients', "
            "'validate-credit-request'))",
        )

    def test_str_falls_back_to_repr(self):
        """``str(expr)`` returns the same as ``repr(expr)``."""
        expr = Or("a") | Self()
        self.assertEqual(str(expr), repr(expr))

    def test_repr_is_evaluable(self):
        """``repr(expr)`` evaluates back to an equivalent expression.

        For composite expressions, ``eval(repr(x))`` round-trips to
        the same type and repr through a namespace that includes the
        DSL classes.  String literals in the repr evaluate to ``str``
        and get auto-wrapped by the outer operation's constructor.

        Note: a standalone ``GateLit("a")`` reprs as ``"'a'"`` —
        evaluating that produces a bare ``str``, not a ``GateLit``.
        This is intentional: ``GateLit`` is an implementation detail
        of the string auto-wrap; users compose via ``Or``/``And``/``Not``
        which accept strings transparently.  Top-level ``GateLit`` is
        therefore excluded from the round-trip assertion.
        """
        cases = [
            Or("activate", "reconvert"),
            And("a", "b"),
            Not("x"),
            Self(),
            Or("a", "b"),
            And("a", Not("b")),
            SELF | "activate",
        ]
        namespace = {
            "Or": Or,
            "And": And,
            "Not": Not,
            "Self": Self,
            "GateLit": GateLit,
        }
        for expr in cases:
            with self.subTest(expr=repr(expr)):
                round_tripped = eval(repr(expr), namespace)  # noqa: S307
                self.assertEqual(type(round_tripped), type(expr))
                self.assertEqual(repr(round_tripped), repr(expr))
