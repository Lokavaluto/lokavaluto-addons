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
