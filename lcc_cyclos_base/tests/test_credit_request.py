import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestFindTopupTransactions(TransactionCase):
    """Test the Cyclos lookup used to reconcile uncertain topups."""

    def setUp(self):
        super().setUp()
        currency_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        self.currency = self.env["res.alt.currency"].create(
            {
                "name": "Cyclos Reconcile",
                "ident": "cyclosreconcile",
                "active": True,
                "engine": "cyclos",
                "currency_unit_product_id": currency_product.id,
                "cyclos_server_url": "https://cyclos.example.org/api",
            }
        )
        partner = self.env["res.partner"].create({"name": "Cyclos User"})
        self.wallet = self.env["res.partner.backend"].create(
            {
                "name": "cyclos:42",
                "ident": "42",
                "cyclos_id": "42",
                "alt_currency_id": self.currency.id,
                "partner_id": partner.id,
            }
        )

    def _raw_tx(self, **overrides):
        """Build a raw transaction as returned by the Cyclos transactions API."""
        raw = {
            "id": "tx-1",
            "amount": "10.00",
            "date": "2026-01-01T10:00:00.000",
            "type": {"internalName": "debit.toUser"},
        }
        raw.update(overrides)
        return raw

    def _patch_rest(self, pages):
        """Mock ``cyclos_rest_call`` with a list of ``(transactions, has_next)``."""
        calls = {"count": 0}

        def fake_rest_call(self, method, entrypoint, data=None, **kwargs):
            transactions, has_next = pages[calls["count"]]
            calls["count"] += 1
            return SimpleNamespace(
                text=json.dumps(transactions),
                headers={"x-has-next-page": "true" if has_next else "false"},
            )

        patcher = patch.object(
            type(self.currency), "cyclos_rest_call", fake_rest_call
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_supports_reconciliation(self):
        """The cyclos engine supports topup reconciliation."""
        self.assertTrue(self.currency._supports_topup_reconciliation())

    def test_matching_transfer_is_returned(self):
        """An incoming transfer with the right amount matches."""
        self._patch_rest([([self._raw_tx()], False)])
        expected_time = int(
            datetime.fromisoformat("2026-01-01T10:00:00.000").timestamp()
        )
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [{"hash": "tx-1", "time": expected_time}])

    def test_different_amount_is_ignored(self):
        """A transfer with a different amount does not match."""
        self._patch_rest([([self._raw_tx(amount="20.00")], False)])
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [])

    def test_outgoing_transfer_is_ignored(self):
        """An outgoing transfer of the same amount does not match."""
        self._patch_rest([([self._raw_tx(amount="-10.00")], False)])
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [])

    def test_incoming_user_payment_is_ignored(self):
        """An incoming payment from another user does not match a topup."""
        self._patch_rest(
            [([self._raw_tx(type={"internalName": "user.toUser"})], False)]
        )
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [])

    def test_transfer_without_id_is_ignored(self):
        """A matching transfer without an id cannot be recorded, so it is skipped."""
        self._patch_rest([([self._raw_tx(id=None)], False)])
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [])

    def test_no_transaction_returns_empty(self):
        """No transaction at all returns no match."""
        self._patch_rest([([], False)])
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [])

    def test_pagination_is_followed(self):
        """Matches on a next page are returned when the API paginates."""
        self._patch_rest(
            [
                ([self._raw_tx(id="tx-other", amount="20.00")], True),
                ([self._raw_tx(id="tx-2")], False),
            ]
        )
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["hash"], "tx-2")
