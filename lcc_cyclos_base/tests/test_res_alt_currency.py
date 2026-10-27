import importlib.util
import json
import os
from unittest.mock import MagicMock, patch

from odoo.modules.module import get_module_path
from odoo.tests.common import TransactionCase

REQUEST_PATH = "odoo.addons.lcc_cyclos_base.models.res_alt_currency.requests.request"


class TestCyclosRestCall(TransactionCase):
    def _create_cyclos_currency(self, **values):
        unit_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        return self.env["res.alt.currency"].create(
            {
                "name": "Currency A",
                "ident": "currencyA",
                "active": True,
                "engine": "cyclos",
                "currency_unit_product_id": unit_product.id,
                "cyclos_server_url": "https://cyclos.example.test/api",
                "cyclos_server_login": "611424",
                "cyclos_server_password": "secret",
                **values,
            }
        )

    def _create_cyclos_wallet(self, currency, is_company=False):
        partner = self.env["res.partner"].create(
            {"name": "Holder", "is_company": is_company}
        )
        return self.env["res.partner.backend"].create(
            {
                "name": "cyclos:4036691651388677992",
                "active": True,
                "alt_currency_id": currency.id,
                "partner_id": partner.id,
                "cyclos_id": "4036691651388677992",
                "cyclos_create_response": "OK",
                "cyclos_status": "active",
            }
        )

    def _sent_requests(self, action, response_text="{}"):
        """Run ``action`` with Cyclos mocked; return the kwargs of each request."""
        response = MagicMock(text=response_text)
        with patch(REQUEST_PATH, return_value=response) as request:
            action()
        return [call.args + (call.kwargs,) for call in request.call_args_list]

    def _sent_headers(self, currency):
        """Run one ``cyclos_rest_call`` and return the HTTP headers it sent."""
        (sent,) = self._sent_requests(lambda: currency.cyclos_rest_call("GET", "/auth"))
        return sent[-1]["headers"]

    def _credit_payment_type(self, wallet):
        (sent,) = self._sent_requests(lambda: wallet.credit_wallet(10))
        return json.loads(sent[-1]["data"])["type"]

    def test_principal_type_header_sent_when_configured(self):
        currency = self._create_cyclos_currency(
            cyclos_server_principal_type="username"
        )
        self.assertEqual(self._sent_headers(currency)["Principal-Type"], "username")

    def test_no_principal_type_header_when_not_configured(self):
        currency = self._create_cyclos_currency()
        self.assertNotIn("Principal-Type", self._sent_headers(currency))

    def test_credit_uses_configured_payment_types(self):
        currency = self._create_cyclos_currency(
            cyclos_credit_payment_type_user="stableAccount.toIndividual",
            cyclos_credit_payment_type_pro="stableAccount.toProfessional",
        )
        self.assertEqual(
            self._credit_payment_type(self._create_cyclos_wallet(currency)),
            "stableAccount.toIndividual",
        )
        self.assertEqual(
            self._credit_payment_type(
                self._create_cyclos_wallet(currency, is_company=True)
            ),
            "stableAccount.toProfessional",
        )

    def test_credit_payment_types_default_to_lokavaluto_cyclos_names(self):
        currency = self._create_cyclos_currency()
        self.assertEqual(
            self._credit_payment_type(self._create_cyclos_wallet(currency)),
            "debit.toUser",
        )
        self.assertEqual(
            self._credit_payment_type(
                self._create_cyclos_wallet(currency, is_company=True)
            ),
            "debit.toPro",
        )

    def test_reconversion_search_uses_configured_account_type(self):
        currency = self._create_cyclos_currency(
            cyclos_reconversion_account_type="stableAccount"
        )
        (sent,) = self._sent_requests(
            lambda: list(currency._retrieve_last_debit_transactions()),
            response_text="[]",
        )
        self.assertIn("toAccountTypes=stableAccount&", sent[1] + "&")

    def test_wallet_balance_is_read_from_cyclos_accounts(self):
        wallet = self._create_cyclos_wallet(self._create_cyclos_currency())
        response = MagicMock(text='[{"status": {"balance": "393.57"}}]')
        with patch(REQUEST_PATH, return_value=response) as request:
            result = wallet.get_wallet_balance()
        self.assertEqual(result, {"success": True, "response": 393.57})
        self.assertTrue(
            request.call_args.args[1].endswith("/4036691651388677992/accounts"),
            request.call_args.args[1],
        )

    def test_password_change_uses_configured_password_type(self):
        currency = self._create_cyclos_currency(cyclos_password_type="login")
        wallet = self._create_cyclos_wallet(currency)
        (sent,) = self._sent_requests(lambda: wallet.force_cyclos_password("pw"))
        self.assertTrue(
            sent[1].endswith("/4036691651388677992/passwords/login/change"), sent[1]
        )

    def test_wallet_ident_set_at_creation(self):
        wallet = self._create_cyclos_wallet(self._create_cyclos_currency())
        self.assertEqual(wallet.ident, "4036691651388677992")
        self.assertTrue(wallet.uri.endswith("/wallet/4036691651388677992"), wallet.uri)

    def test_reconversion_yields_uri_of_sender_wallet(self):
        currency = self._create_cyclos_currency()
        wallet = self._create_cyclos_wallet(currency)
        transactions = [
            {
                "id": "4036655354888494952",
                "date": "2026-10-27T10:00:00.000+01:00",
                "amount": "1.00",
                "from": {"user": {"id": "4036691651388677992"}},
            }
        ]
        response = MagicMock(text=json.dumps(transactions))
        with patch(REQUEST_PATH, return_value=response), patch.object(
            self.env.cr, "commit"
        ):
            (transaction,) = list(currency._retrieve_last_debit_transactions())
        self.assertEqual(transaction["wallet_uri"], wallet.uri)
        self.assertNotIn("sender", transaction)

    def _registration_group(self, currency, is_company=False):
        partner = self.env["res.partner"].create(
            {"name": "New holder", "is_company": is_company}
        )
        (sent,) = self._sent_requests(
            lambda: partner.cyclos_add_user(currency),
            response_text='{"user": {"id": "1234"}, "status": "active"}',
        )
        return json.loads(sent[-1]["data"])["group"]

    def test_registration_uses_configured_groups(self):
        currency = self._create_cyclos_currency(
            cyclos_user_group_person="individual",
            cyclos_user_group_company="professional",
        )
        self.assertEqual(self._registration_group(currency), "individual")
        self.assertEqual(
            self._registration_group(currency, is_company=True), "professional"
        )

    def test_registration_groups_default_to_lokavaluto_cyclos_names(self):
        currency = self._create_cyclos_currency()
        self.assertEqual(self._registration_group(currency), "particuliers")
        self.assertEqual(
            self._registration_group(currency, is_company=True), "professionnels"
        )

class TestCyclosWalletIdentMigration(TransactionCase):
    """Wallets created before ``ident`` was set at creation get it back."""

    def _migrate(self):
        path = get_module_path("lcc_cyclos_base")
        spec = importlib.util.spec_from_file_location(
            "lcc_cyclos_base_post_migrate_16_0_1_2_1",
            os.path.join(path, "migrations", "16.0.1.2.1", "post-migrate.py"),
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, "16.0.1.2.0")
        self.env.invalidate_all()

    def _wallet(self, currency, cyclos_id, ident):
        partner = self.env["res.partner"].create({"name": f"Holder {cyclos_id}"})
        wallet = self.env["res.partner.backend"].create(
            {
                "name": f"cyclos:{cyclos_id}",
                "alt_currency_id": currency.id,
                "partner_id": partner.id,
                "cyclos_id": cyclos_id,
            }
        )
        ## Simulate wallets stored before the fix, bypassing the ORM.
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE res_partner_backend SET ident = %s, uri = %s WHERE id = %s",
            (ident, f"{currency.uri}/wallet/{ident}", wallet.id),
        )
        self.env.invalidate_all(flush=False)
        return wallet

    def test_missing_wallet_ident_filled_from_cyclos_id(self):
        currency = self.env["res.alt.currency"].create(
            {"name": "C", "ident": "cyclos.example.test", "engine": "cyclos"}
        )
        missing = self._wallet(currency, "111", None)
        kept = self._wallet(currency, "222", "already-set")

        self._migrate()

        self.assertEqual(missing.ident, "111")
        self.assertEqual(missing.uri, f"{currency.uri}/wallet/111")
        self.assertEqual(kept.ident, "already-set")
