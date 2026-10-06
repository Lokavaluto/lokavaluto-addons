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

    def _sent_headers(self, currency):
        """Run one ``cyclos_rest_call`` and return the HTTP headers it sent."""
        response = MagicMock(text="{}")
        with patch(REQUEST_PATH, return_value=response) as request:
            currency.cyclos_rest_call("GET", "/auth")
        request.assert_called_once()
        return request.call_args.kwargs["headers"]

    def test_principal_type_header_sent_when_configured(self):
        currency = self._create_cyclos_currency(
            cyclos_server_principal_type="username"
        )
        self.assertEqual(self._sent_headers(currency)["Principal-Type"], "username")

    def test_no_principal_type_header_when_not_configured(self):
        currency = self._create_cyclos_currency()
        self.assertNotIn("Principal-Type", self._sent_headers(currency))
