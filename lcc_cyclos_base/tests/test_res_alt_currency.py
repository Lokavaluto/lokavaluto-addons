import json
from unittest.mock import MagicMock, patch

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

    def test_password_change_uses_configured_password_type(self):
        currency = self._create_cyclos_currency(cyclos_password_type="login")
        wallet = self._create_cyclos_wallet(currency)
        (sent,) = self._sent_requests(lambda: wallet.force_cyclos_password("pw"))
        self.assertTrue(
            sent[1].endswith("/4036691651388677992/passwords/login/change"), sent[1]
        )
