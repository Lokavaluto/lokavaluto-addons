from unittest.mock import patch

from minimock import Mock

from odoo.addons.component.tests.common import TransactionComponentCase
import odoo.addons.lcc_lokavaluto_app_connection.services as svc
from odoo.addons.lcc_lokavaluto_app_connection.datamodel.payment_request_info import (
    ListPaymentRequestsParams,
)


class TestPaymentRequestServices(TransactionComponentCase):
    """Payment request API as Monujo calls it for cyclos wallets."""

    def _create_user(self):
        company = self.env["res.company"].create({"name": "Acme Corp"})
        partner = self.env["res.partner"].create({"name": "John Doe"})
        user = self.env["res.users"].create(
            {
                "login": "jdoe",
                "partner_id": partner.id,
                "company_id": company.id,
                "company_ids": [(6, 0, [company.id])],
            }
        )
        return user

    def _create_cyclos_currency(self, domain):
        return self.env["res.alt.currency"].create(
            {
                "name": domain,
                "ident": domain,
                "engine": "cyclos",
                "currency_unit_product_id": self.env.ref(
                    "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
                ).id,
                "cyclos_server_url": f"https://{domain}/api",
            }
        )

    def _create_cyclos_wallet(self, partner, currency, owner_id):
        return self.env["res.partner.backend"].create(
            {
                "name": f"cyclos:{owner_id}",
                "alt_currency_id": currency.id,
                "partner_id": partner.id,
                "cyclos_id": owner_id,
                "ident": owner_id,
            }
        )

    def _list_payment_requests(self, user, currency_uri, wallet_uri, caller_user_uri):
        """Call the endpoint with the caller header Monujo always sends."""
        mock_request = Mock(
            "request",
            httprequest=Mock(
                "httprequest",
                headers={"X-Lokapi-Caller-User-Uri": caller_user_uri},
            ),
        )
        collection = self.env["lokavaluto.private.services"].with_user(user).browse(1)
        with collection.work_on("payment.request") as work, patch.object(
            svc, "request", mock_request
        ):
            service = work.component(usage="payment_request")
            return service.list_payment_requests(
                list_payment_requests_params=ListPaymentRequestsParams(
                    currency_uri=currency_uri, wallet_uri=wallet_uri
                )
            )

    def test_list_payment_requests_with_monujo_cyclos_key(self):
        """Monujo's ``cyclos:<id>@<host>`` key finds the wallet, and the
        wallet keys in the answer use that same form."""
        user = self._create_user()
        currency = self._create_cyclos_currency("cyclos.example.org")
        wallet_1 = self._create_cyclos_wallet(user.partner_id, currency, "-111")
        wallet_2 = self._create_cyclos_wallet(user.partner_id, currency, "-222")
        self.env["payment.request"].create(
            {
                "creator_wallet_id": wallet_1.id,
                "alt_currency_id": currency.id,
                "sender_wallet_id": wallet_2.id,
                "receiver_wallet_id": wallet_1.id,
                "amount": 10.0,
            }
        )

        payment_requests = self._list_payment_requests(
            user,
            "cyclos://cyclos.example.org",
            "cyclos:-111@cyclos.example.org",
            caller_user_uri="cyclos://cyclos.example.org/user/-111",
        )

        self.assertEqual(len(payment_requests), 1)
        self.assertEqual(
            [
                payment_requests[0]["creator_wallet_uri"],
                payment_requests[0]["sender_wallet_uri"],
                payment_requests[0]["receiver_wallet_uri"],
            ],
            [
                "cyclos:-111@cyclos.example.org",
                "cyclos:-222@cyclos.example.org",
                "cyclos:-111@cyclos.example.org",
            ],
        )
