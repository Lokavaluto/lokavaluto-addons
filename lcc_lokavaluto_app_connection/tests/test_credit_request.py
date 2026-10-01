from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.lcc_lokavaluto_app_connection.models.credit_request import (
    CreditRequest,
)


class TestCreditRequestDurableAttempt(TransactionCase):
    """Test the durable, per-request processing of pending credit requests.

    The post-commit hook is not executed by the test cursor, so the raw
    (undecorated) body of ``_check_pending_requests_to_credit`` is invoked
    directly through ``__wrapped__``.
    """

    def setUp(self):
        super().setUp()
        self.CreditRequest = self.env["credit.request"]
        currency_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        self.currency = self.env["res.alt.currency"].create(
            {
                "name": "Durable Test",
                "ident": "durabletest",
                "active": True,
                "engine": "foo",
                "activate_automatic_topup": True,
                "currency_unit_product_id": currency_product.id,
            }
        )
        self.partner = self.env["res.partner"].create({"name": "Durable User"})
        self.wallet = self.env["res.partner.backend"].create(
            {
                "name": "foo:durabletest:1",
                "ident": "1",
                "alt_currency_id": self.currency.id,
                "partner_id": self.partner.id,
            }
        )

    def _make_pending_request(self, amount=10.0):
        return self.CreditRequest.create(
            {
                "wallet_id": self.wallet.id,
                "amount": amount,
                "state": "pending",
                "no_order": True,
            }
        )

    def _patch_cursor_transactions(self):
        """Neutralize commit/rollback on the test cursor.

        ``_run_credit_attempt`` commits between the intent and the outcome;
        the test cursor turns a commit into a savepoint release, which then
        breaks the error-path rollback. Patching both keeps the logic under
        test (ordering, isolation) without touching the test transaction.
        """
        for method_name in ("commit", "rollback"):
            patcher = patch.object(type(self.env.cr), method_name)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_failed_request_does_not_abort_the_batch(self):
        """A failing request must not roll back or abort the other ones."""
        self._patch_cursor_transactions()
        req1 = self._make_pending_request(1.0)
        req2 = self._make_pending_request(2.0)
        req3 = self._make_pending_request(3.0)

        def fake_credit_wallet(records):
            for record in records:
                if record.id == req2.id:
                    raise Exception("boom")
                record.write({"state": "done"})

        with patch.object(CreditRequest, "credit_wallet", fake_credit_wallet):
            CreditRequest._check_pending_requests_to_credit.__wrapped__(
                req1 | req2 | req3
            )

        self.assertEqual(req1.state, "done")
        self.assertEqual(req3.state, "done")
        self.assertEqual(req2.state, "pending")
        self.assertTrue(req2.send_started_at)
        self.assertEqual(req2.send_attempt_count, 1)

    def test_intent_is_persisted_before_external_call(self):
        """`send_started_at` and the attempt counter are set before sending."""
        self._patch_cursor_transactions()
        request = self._make_pending_request()
        observed = {}

        def fake_credit_wallet(records):
            record = records[0]
            observed["send_started_at"] = record.send_started_at
            observed["send_attempt_count"] = record.send_attempt_count
            record.write({"state": "done"})

        with patch.object(CreditRequest, "credit_wallet", fake_credit_wallet):
            request._run_credit_attempt()

        self.assertTrue(observed["send_started_at"])
        self.assertEqual(observed["send_attempt_count"], 1)
        self.assertEqual(request.state, "done")

    def test_disabled_auto_topup_is_skipped(self):
        """A pending request is not sent when automatic topup is disabled."""
        self.currency.activate_automatic_topup = False
        request = self._make_pending_request()
        sent_ids = []

        def fake_credit_wallet(records):
            sent_ids.append(records.ids)

        with patch.object(CreditRequest, "credit_wallet", fake_credit_wallet):
            CreditRequest._check_pending_requests_to_credit.__wrapped__(request)

        self.assertFalse(sent_ids)
