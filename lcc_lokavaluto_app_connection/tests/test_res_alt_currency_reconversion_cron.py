from contextlib import contextmanager
from unittest.mock import call, patch

from odoo.addons.component.tests.common import TransactionComponentCase


class TestReconversionCron(TransactionComponentCase):
    """The reconversion cron must import each currency independently.

    A failing currency must not prevent the others from being imported,
    and must still be reported as a failure of the cron run.
    """

    def setUp(self):
        super().setUp()
        self.ResAltCurrency = self.env["res.alt.currency"]

    def _create_alt_currency(self, ident):
        return self.ResAltCurrency.create(
            {"name": ident, "ident": ident, "active": True, "engine": "foo"}
        )

    @contextmanager
    def _patched_cron_run(self, failing=()):
        """Record which currencies are synced, and the transaction calls.

        Currencies listed in ``failing`` raise when synced. Currencies
        not created by the test (if any exist in the database) are
        synced as a no-op. Yields ``(synced, cursor)`` where ``synced``
        is the list of synced currency names and ``cursor`` is a mock
        recording ``commit`` and ``rollback`` calls in order.
        """
        synced = []
        failing_ids = {c.id for c in failing}

        def fake_sync(currency, start=None, end=None):
            synced.append(currency.name)
            if currency.id in failing_ids:
                raise ValueError(f"sync failure on {currency.name}")

        with patch.object(
            type(self.ResAltCurrency),
            "_sync_new_debit_requests",
            autospec=True,
            side_effect=fake_sync,
        ), patch.object(self.env.cr, "commit") as commit, patch.object(
            self.env.cr, "rollback"
        ) as rollback:
            cursor = commit.__class__()
            cursor.attach_mock(commit, "commit")
            cursor.attach_mock(rollback, "rollback")
            yield synced, cursor

    def test_failing_currency_does_not_block_the_others(self):
        broken = self._create_alt_currency("broken")
        healthy = self._create_alt_currency("healthy")

        with self._patched_cron_run(failing=[broken]) as (synced, _cursor):
            with self.assertRaisesRegex(Exception, r"broken") as ctx:
                self.ResAltCurrency._cron_import_new_digital_currency_debit_requests()

        self.assertIn("healthy", synced)
        self.assertIn("broken", synced)
        self.assertNotIn("healthy", str(ctx.exception))

    def test_all_currencies_succeed(self):
        self._create_alt_currency("first")
        self._create_alt_currency("second")

        with self._patched_cron_run() as (synced, _cursor):
            self.ResAltCurrency._cron_import_new_digital_currency_debit_requests()

        self.assertIn("first", synced)
        self.assertIn("second", synced)

    def test_failed_currency_is_rolled_back_successful_one_committed(self):
        healthy = self._create_alt_currency("healthy")
        broken = self._create_alt_currency("broken")
        currencies = healthy | broken

        with self._patched_cron_run(failing=[broken]) as (_synced, cursor):
            with patch.object(
                type(self.ResAltCurrency), "search", return_value=currencies
            ), self.assertRaises(Exception):
                self.ResAltCurrency._cron_import_new_digital_currency_debit_requests()

        self.assertEqual(cursor.mock_calls, [call.commit(), call.rollback()])

    def test_single_currency_error_propagates_unchanged(self):
        broken = self._create_alt_currency("broken")

        with self._patched_cron_run(failing=[broken]) as (synced, cursor):
            with self.assertRaisesRegex(ValueError, r"^sync failure on broken$"):
                self.ResAltCurrency._cron_import_new_digital_currency_debit_requests(
                    currency_uri=broken.uri
                )

        self.assertEqual(synced, ["broken"])
        self.assertEqual(cursor.mock_calls, [])
