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


class TestGetAuthorizedActionsReconvert(TransactionCase):
    """Test ``reconvert`` action contribution in ``get_authorized_actions``.

    Base ``get_authorized_actions()`` contributes ``reconvert`` when
    ``is_reconversion_allowed`` is True.  Eligibility is driven by the
    ``reconversion.rule`` table (first-match-wins, default False).

    ``reconvert`` is a *user action*, not an admin action: it must
    never trigger the ``ANY_ADMIN_ACTION`` gate by itself.  That
    invariant is covered by separate tests at the service layer.
    """

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
        ## Purge any pre-existing rules (from prior manual seeding or
        ## earlier test runs on the same DB) so first-match-wins is
        ## deterministic.  TransactionCase rolls this back on teardown.
        self.env["reconversion.rule"].search([]).unlink()

    def _make_wallet(self, login="alice"):
        user = self.env["res.users"].create(
            {"name": login.capitalize(), "login": login}
        )
        wallet = self.env["res.partner.backend"].create(
            {
                "partner_id": user.partner_id.id,
                "name": f"foo:0x{login}",
                "ident": f"0x{login}",
                "alt_currency_id": self.currency.id,
            }
        )
        wallet.status = "active"
        return wallet

    def _make_rule(self, name, allowed, sequence=10, wallet_domain="[]"):
        return self.env["reconversion.rule"].create(
            {
                "name": name,
                "sequence": sequence,
                "active": True,
                "wallet_domain": wallet_domain,
                "is_reconversion_allowed": allowed,
            }
        )

    def test_returns_empty_when_no_rule_matches(self):
        """Default: no rules → ``reconvert`` not included."""
        wallet = self._make_wallet()
        self.assertEqual(wallet.get_authorized_actions(), [])

    def test_returns_reconvert_when_matching_rule_allows(self):
        """Rule allowing reconversion → ``reconvert`` present."""
        wallet = self._make_wallet()
        self._make_rule("allow-all", allowed=True)
        self.assertIn("reconvert", wallet.get_authorized_actions())

    def test_omits_reconvert_when_matching_rule_denies(self):
        """Rule explicitly denying → no ``reconvert``."""
        wallet = self._make_wallet()
        self._make_rule("deny-all", allowed=False)
        self.assertNotIn("reconvert", wallet.get_authorized_actions())

    def test_first_matching_rule_wins_deny_over_allow(self):
        """Earlier-sequence deny rule shadows later allow rule."""
        wallet = self._make_wallet()
        self._make_rule("deny-first", allowed=False, sequence=1)
        self._make_rule("allow-second", allowed=True, sequence=2)
        self.assertNotIn("reconvert", wallet.get_authorized_actions())

    def test_first_matching_rule_wins_allow_over_deny(self):
        """Earlier-sequence allow rule shadows later deny rule."""
        wallet = self._make_wallet()
        self._make_rule("allow-first", allowed=True, sequence=1)
        self._make_rule("deny-second", allowed=False, sequence=2)
        self.assertIn("reconvert", wallet.get_authorized_actions())

    def test_inactive_rule_is_ignored(self):
        """Inactive rules do not participate in eligibility."""
        wallet = self._make_wallet()
        rule = self._make_rule("inactive-allow", allowed=True)
        rule.active = False
        self.assertNotIn("reconvert", wallet.get_authorized_actions())

    def test_wallet_domain_filters_match(self):
        """Rule with a non-matching domain does not apply."""
        wallet = self._make_wallet("alice")
        self._make_rule(
            "narrow",
            allowed=True,
            wallet_domain="[('ident', '=', '0xnoone')]",
        )
        self.assertNotIn("reconvert", wallet.get_authorized_actions())

    def test_returns_sorted_list(self):
        """``get_authorized_actions`` returns a sorted list (stable API)."""
        wallet = self._make_wallet()
        self._make_rule("allow-all", allowed=True)
        actions = wallet.get_authorized_actions()
        self.assertEqual(actions, sorted(actions))


class TestPaymentRequestAllowedRule(TransactionCase):
    """Test payment.request.allowed.rule computed field on wallet."""

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
        self.PaymentRequestAllowedRule = self.env["payment.request.allowed.rule"]
        self.ResPartnerBackend = self.env["res.partner.backend"]

    def _make_wallet(self, name="foo:testwallet", ident="testwallet"):
        partner = self.env["res.partner"].create({"name": name})
        return self.ResPartnerBackend.create(
            {
                "partner_id": partner.id,
                "name": name,
                "ident": ident,
                "alt_currency_id": self.currency.id,
            }
        )

    def _create_payment_request_allowed_rule(
        self,
        wallet_domain="[]",
        is_payment_request_allowed=True,
        sequence=None,
        active=True,
    ):
        vals = {
            "name": "Test Rule",
            "active": active,
            "wallet_domain": wallet_domain,
            "is_payment_request_allowed": is_payment_request_allowed,
        }
        if sequence is not None:
            vals["sequence"] = sequence
        return self.PaymentRequestAllowedRule.create(vals)

    def test_default_is_not_allowed(self):
        """When no rule exists, is_payment_request_allowed is False."""
        wallet = self._make_wallet()
        self.assertFalse(wallet.is_payment_request_allowed)

    def test_allowed_by_rule(self):
        """A matching rule can allow payment requests."""
        self._create_payment_request_allowed_rule()
        wallet = self._make_wallet()
        self.assertTrue(wallet.is_payment_request_allowed)

    def test_blocked_by_rule(self):
        """A matching rule can block payment requests."""
        self._create_payment_request_allowed_rule(
            is_payment_request_allowed=False,
        )
        wallet = self._make_wallet()
        self.assertFalse(wallet.is_payment_request_allowed)

    def test_first_matching_rule_wins(self):
        """Rules are ordered by sequence; the first match applies."""
        self._create_payment_request_allowed_rule(
            sequence=0,
            is_payment_request_allowed=False,
        )
        self._create_payment_request_allowed_rule(
            sequence=10,
        )
        wallet = self._make_wallet()
        # First matching rule (sequence 0) says False
        self.assertFalse(wallet.is_payment_request_allowed)

    def test_rule_with_specific_domain(self):
        """Only wallets matching the domain are affected."""
        self._create_payment_request_allowed_rule(
            wallet_domain="[('name', '=', 'foo:target')]",
            is_payment_request_allowed=False,
        )
        target_wallet = self._make_wallet(name="foo:target", ident="target")
        other_wallet = self._make_wallet(name="foo:other", ident="other")
        self.assertFalse(target_wallet.is_payment_request_allowed)
        # Other wallet keeps default (False) since no rule matches it
        self.assertFalse(other_wallet.is_payment_request_allowed)

    def test_rule_with_specific_domain_allows(self):
        """A rule can explicitly allow a targeted wallet."""
        self._create_payment_request_allowed_rule(
            wallet_domain="[('name', '=', 'foo:premium')]",
        )
        premium_wallet = self._make_wallet(name="foo:premium", ident="premium")
        other_wallet = self._make_wallet(name="foo:basic", ident="basic")
        self.assertTrue(premium_wallet.is_payment_request_allowed)
        self.assertFalse(other_wallet.is_payment_request_allowed)

    def test_inactive_rule_is_ignored(self):
        """Inactive rules are skipped."""
        self._create_payment_request_allowed_rule(
            active=False,
            is_payment_request_allowed=False,
        )
        wallet = self._make_wallet()
        # No active rule matches -> default is False
        self.assertFalse(wallet.is_payment_request_allowed)
