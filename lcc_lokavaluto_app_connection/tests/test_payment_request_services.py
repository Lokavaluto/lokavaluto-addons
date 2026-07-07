from ..datamodel.payment_request_info import (
    CreatePaymentRequestParam,
    ListPaymentRequestsParams,
    UpdatePaymentRequestParams
)
from odoo.addons.component.tests.common import TransactionComponentCase
from odoo.exceptions import AccessDenied, ValidationError
from ..tools import transform_wallet_uris_in_wallet_backend_keys


class TestResWallet(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        self.ResCompany = self.env["res.company"]
        self.ResUsers = self.env["res.users"]
        self.ResPartner = self.env["res.partner"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.ResAltCurrency = self.env["res.alt.currency"]
        self.PaymentRequest = self.env["payment.request"]
        self.Services = self.env["lokavaluto.private.services"]

    def _create_company(self, name="Acme Corp"):
        return self.ResCompany.create({"name": name})

    def _create_res_partner(self, name="John Doe"):
        return self.ResPartner.create({"name": name})

    def _create_res_user(self, login="jdoe", partner=None, company=None):
        return self.ResUsers.create({
            "login": login,
            "partner_id": partner.id,
            "company_id": company.id,
            "company_ids": [(6, 0, [company.id])],
        })

    def _create_alt_currency(self, ident="currency", safe_wallet_partner_id=None):
        return self.ResAltCurrency.create(
            {
                "name": ident,
                "ident": ident,
                "active": True,
                "engine": "foo",
            }
        )

    def _create_res_partner_backend(self, partner, currency, ident="98765"):
        return self.ResPartnerBackend.create(
            {
                "name": f"foo:{ident}",
                "alt_currency_id": currency.id,
                "partner_id": partner.id,
                "ident": ident
            }
        )

    def _create_payment_request(self, creator_wallet, sender_wallet, receiver_wallet, amount, message):
        return self.PaymentRequest.create(
            {
                "creator_wallet_id": creator_wallet.id,
                "alt_currency_id": creator_wallet.alt_currency_id.id,
                "sender_wallet_id": sender_wallet.id,
                "receiver_wallet_id": receiver_wallet.id,
                "amount": amount,
                "message": message,
            }
        )

    def _create_payment_request_allowed_rule(self):
        self.env["payment.request.allowed.rule"].create(
            {
                "name": "Allow all",
                "wallet_domain": "[]",
                "is_payment_request_allowed": True,
            }
        )

    def test_payment_request_service_create_1(self):
        """Test creating a payment request via the service"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        self._create_payment_request_allowed_rule()
        collection = self.Services.with_user(user).browse(1)

        # Use service to create payment request
        # The creator is the receiver of the payment request
        with collection.work_on("payment.request") as work:
            service = work.component(usage="payment_request")
            params = CreatePaymentRequestParam(
                currency_uri=currency.uri,
                creator_wallet_uri=wallet_1.uri,
                requests=[
                    {
                        "sender_wallet_uri": wallet_2.uri,
                        "receiver_wallet_uri": wallet_1.uri,
                        "amount": 50.0,
                        "message": "Test Payment Request creation 1",
                    }
                ]
            )
            res = service.create_payment_request(params)
            self.assertTrue(res)
            payment_request = self.PaymentRequest.browse(res)
            self.assertEqual(payment_request.creator_wallet_id.id, wallet_1.id)
            self.assertEqual(payment_request.sender_wallet_id.id, wallet_2.id)
            self.assertEqual(payment_request.receiver_wallet_id.id, wallet_1.id)
            self.assertEqual(payment_request.amount, 50.0)
            self.assertEqual(payment_request.message, "Test Payment Request creation 1")

    def test_payment_request_service_create_2(self):
        """Create a payment request where sender and creator are the same wallet"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        self._create_payment_request_allowed_rule()
        collection = self.Services.with_user(user).browse(1)

        # Use service to create payment request
        # The creator is the receiver of the payment request
        with collection.work_on("payment.request") as work:
            service = work.component(usage="payment_request")
            params = CreatePaymentRequestParam(
                currency_uri=currency.uri,
                creator_wallet_uri=wallet_1.uri,
                requests=[
                    {
                        "sender_wallet_uri": wallet_1.uri,
                        "receiver_wallet_uri": wallet_2.uri,
                        "amount": 50.0,
                        "message": "Test Payment Request creation 2",
                    }
                ]
            )
            res = service.create_payment_request(params)
            self.assertTrue(res)
            payment_request = self.PaymentRequest.browse(res)
            self.assertEqual(payment_request.creator_wallet_id.id, wallet_1.id)
            self.assertEqual(payment_request.sender_wallet_id.id, wallet_1.id)
            self.assertEqual(payment_request.receiver_wallet_id.id, wallet_2.id)
            self.assertEqual(payment_request.amount, 50.0)
            self.assertEqual(payment_request.message, "Test Payment Request creation 2")

    def test_payment_request_service_create_blocked_if_not_allowed(self):
        """Creating payment requests is denied when is_payment_request_allowed is False."""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        # No payment.request.allowed.rule created → default is False
        collection = self.Services.with_user(user).browse(1)

        with collection.work_on("payment.request") as work:
            service = work.component(usage="payment_request")
            params = CreatePaymentRequestParam(
                currency_uri=currency.uri,
                creator_wallet_uri=wallet_1.uri,
                requests=[
                    {
                        "sender_wallet_uri": wallet_2.uri,
                        "receiver_wallet_uri": wallet_1.uri,
                        "amount": 50.0,
                        "message": "Should be blocked",
                    }
                ],
            )
            with self.assertRaises(AccessDenied):
                service.create_payment_request(params)

    def test_payment_request_service_create_allowed_by_rule(self):
        """Creating payment requests succeeds when a matching rule allows it."""
        self._create_payment_request_allowed_rule()
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        collection = self.Services.with_user(user).browse(1)

        with collection.work_on("payment.request") as work:
            service = work.component(usage="payment_request")
            params = CreatePaymentRequestParam(
                currency_uri=currency.uri,
                creator_wallet_uri=wallet_1.uri,
                requests=[
                    {
                        "sender_wallet_uri": wallet_2.uri,
                        "receiver_wallet_uri": wallet_1.uri,
                        "amount": 50.0,
                        "message": "Allowed by rule",
                    }
                ],
            )
            res = service.create_payment_request(params)
            self.assertTrue(res)
            payment_request = self.PaymentRequest.browse(res)
            self.assertEqual(payment_request.creator_wallet_id.id, wallet_1.id)

    def test_payment_request_service_list_1(self):
        """List payment requests for a given wallet"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        wallet_3 = self._create_res_partner_backend(partner, currency, ident="54321")
        payment_request_1 = self._create_payment_request(
            creator_wallet=wallet_1,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_1,
            amount=75.0,
            message="First Payment Request"
        )
        payment_request_2 = self._create_payment_request(
            creator_wallet=wallet_1,
            sender_wallet=wallet_1,
            receiver_wallet=wallet_2,
            amount=125.0,
            message="Second Payment Request"
        )
        payment_request_2.state = "paid"  # Mark second request as paid
        payment_request_3 = self._create_payment_request(
            creator_wallet=wallet_3,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_3,
            amount=200.0,
            message="Third Payment Request"
        )
        collection = self.Services.with_user(user).browse(1)

        # Use service to list payment requests for wallet_1
        with collection.work_on("payment.request") as work:
            service = work.component(usage="payment_request")
            params = ListPaymentRequestsParams(
                currency_uri=currency.uri,
                wallet_uri=wallet_1.uri
            )
            payment_requests = service.list_payment_requests(
                list_payment_requests_params=params
            )
            wallet_1_backend_key = transform_wallet_uris_in_wallet_backend_keys(
                [wallet_1.uri]
            )[0]
            wallet_2_backend_key = transform_wallet_uris_in_wallet_backend_keys(
                [wallet_2.uri]
            )[0]
            expected_requests = [
                {
                    "id": payment_request_1.id,
                    "create_date": payment_requests[0]["create_date"],
                    "creator_name": partner.name,
                    "creator_wallet_uri": wallet_1_backend_key,
                    "sender_name": partner.name,
                    "sender_partner_id": partner.id,
                    "sender_wallet_uri": wallet_2_backend_key,
                    "receiver_name": partner.name,
                    "receiver_partner_id": partner.id,
                    "receiver_wallet_uri": wallet_1_backend_key,
                    "amount": 75.0,
                    "message": "First Payment Request",
                    "state": "open",
                },
                {
                    "id": payment_request_2.id,
                    "create_date": payment_requests[1]["create_date"],
                    "creator_name": partner.name,
                    "creator_wallet_uri": wallet_1_backend_key,
                    "sender_name": partner.name,
                    "sender_partner_id": partner.id,
                    "sender_wallet_uri": wallet_1_backend_key,
                    "receiver_name": partner.name,
                    "receiver_partner_id": partner.id,
                    "receiver_wallet_uri": wallet_2_backend_key,
                    "amount": 125.0,
                    "message": "Second Payment Request",
                    "state": "paid",
                },
            ]
            self.maxDiff = None
            self.assertEqual(len(payment_requests), 2)
            self.assertEqual(payment_requests, expected_requests)

    def test_payment_request_service_list_2(self):
        """List payment requests for a given wallet and state filter"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        payment_request_1 = self._create_payment_request(
            creator_wallet=wallet_1,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_1,
            amount=75.0,
            message="First Payment Request"
        )
        payment_request_2 = self._create_payment_request(
            creator_wallet=wallet_1,
            sender_wallet=wallet_1,
            receiver_wallet=wallet_2,
            amount=125.0,
            message="Second Payment Request"
        )
        payment_request_2.state = "paid"  # Mark second request as paid
        collection = self.Services.with_user(user).browse(1)

        # Use service to list payment requests for wallet_1
        with collection.work_on("payment.request") as work:
            service = work.component(usage="payment_request")
            params = ListPaymentRequestsParams(
                currency_uri=currency.uri,
                wallet_uri=wallet_1.uri,
                state=["paid"]
            )
            payment_requests = service.list_payment_requests(
                list_payment_requests_params=params
            )
            wallet_1_backend_key = transform_wallet_uris_in_wallet_backend_keys(
                [wallet_1.uri]
            )[0]
            wallet_2_backend_key = transform_wallet_uris_in_wallet_backend_keys(
                [wallet_2.uri]
            )[0]
            expected_requests = [
                {
                    "id": payment_request_2.id,
                    "create_date": payment_requests[0]["create_date"],
                    "creator_name": partner.name,
                    "creator_wallet_uri": wallet_1_backend_key,
                    "sender_name": partner.name,
                    "sender_partner_id": partner.id,
                    "sender_wallet_uri": wallet_1_backend_key,
                    "receiver_name": partner.name,
                    "receiver_partner_id": partner.id,
                    "receiver_wallet_uri": wallet_2_backend_key,
                    "amount": 125.0,
                    "message": "Second Payment Request",
                    "state": "paid",
                },
            ]
            self.maxDiff = None
            self.assertEqual(len(payment_requests), 1)
            self.assertEqual(payment_requests, expected_requests)

    def test_payment_request_service_update_1(self):
        """Update a payment request to 'paid' status

        To pay a payment request, you must :
        1. be the user that owns the sender wallet
        2. perform the payment from the sender wallet

        In this test, both conditions are met. Update should succeed.
        """
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        payment_request = self._create_payment_request(
            creator_wallet=wallet_1,
            sender_wallet=wallet_1,
            receiver_wallet=wallet_2,
            amount=100.0,
            message="Payment Request to be updated"
        )
        collection = self.Services.with_user(user).browse(1)

        # Use service to update the payment request
        with collection.work_on("payment.request") as work:
            service = work.component(usage="payment_request")
            params = UpdatePaymentRequestParams(
                currency_uri=currency.uri,
                payment_request_id=payment_request.id,
                wallet_uri=wallet_1.uri,
                status="paid",
                message="test_tx_id",
            )
            res = service.update_payment_request(
                update_payment_request_params=params
            )
            self.assertTrue(res)
            self.assertEqual(payment_request.state, "paid")
            self.assertEqual(payment_request.tx_id, "test_tx_id")

    def test_payment_request_service_update_2(self):
        """Attempt to update a payment request with wrong user.

        To update a payment request, you must  be the user that owns the wallet
        provided in the params

        In this test, this condition is not met. Update should fail.
        """
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner_1 = self._create_res_partner()
        user_1 = self._create_res_user(partner=partner_1, company=company)
        wallet_1 = self._create_res_partner_backend(partner_1, currency, ident="12345")
        partner_2 = self._create_res_partner()
        user_2 = self._create_res_user(login="jdoe2", partner=partner_2, company=company)
        wallet_2 = self._create_res_partner_backend(partner_2, currency, ident="67890")
        payment_request = self._create_payment_request(
            creator_wallet=wallet_1,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_1,
            amount=100.0,
            message="Payment Request to be updated"
        )
        collection = self.Services.with_user(user_1).browse(1)
        # Use service to update the payment request by the sender wallet
        with collection.work_on("payment.request") as work:
            service = work.component(usage="payment_request")
            params = UpdatePaymentRequestParams(
                currency_uri=currency.uri,
                payment_request_id=payment_request.id,
                wallet_uri=wallet_2.uri,
                status="paid",
                message="test_tx_id",
            )
            with self.assertRaises(ValidationError) as context:
                service.update_payment_request(
                    update_payment_request_params=params
                )
            self.assertEqual(payment_request.state, "open")
            self.assertIn("Only wallet owners can make the payment request update", str(context.exception))

    def test_payment_request_service_update_3(self):
        """Attempt to update a payment request with paid status by the wrong WALLET.

        To pay a payment request, you must :
        1. be the user that owns the sender wallet
        2. perform the payment from the sender wallet

        In this test, condition 2 is not met. Update should fail.
        """
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner_1 = self._create_res_partner()
        user_1 = self._create_res_user(partner=partner_1, company=company)
        wallet_1 = self._create_res_partner_backend(partner_1, currency, ident="12345")
        partner_2 = self._create_res_partner()
        user_2 = self._create_res_user(login="jdoe2", partner=partner_2, company=company)
        wallet_2 = self._create_res_partner_backend(partner_2, currency, ident="67890")
        payment_request = self._create_payment_request(
            creator_wallet=wallet_1,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_1,
            amount=100.0,
            message="Payment Request to be updated"
        )
        collection = self.Services.with_user(user_1).browse(1)
        # Use service to update the payment request by the sender wallet
        with collection.work_on("payment.request") as work:
            service = work.component(usage="payment_request")
            params = UpdatePaymentRequestParams(
                currency_uri=currency.uri,
                payment_request_id=payment_request.id,
                wallet_uri=wallet_1.uri,
                status="paid",
                message="test_tx_id",
            )
            with self.assertRaises(ValidationError) as context:
                service.update_payment_request(
                    update_payment_request_params=params
                )
            self.assertEqual(payment_request.state, "open")
            self.assertIn("Only the sender wallet can mark the payment request as paid", str(context.exception))

    def test_payment_request_service_update_4(self):
        """Update a payment request to 'cancelled' status

        To cancel a payment request, you must :
        1. be the user that owns the creator wallet
        2. perform the cancellation from the creator wallet

        In this test, both conditions are met. Update should succeed.
        """

        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        payment_request = self._create_payment_request(
            creator_wallet=wallet_1,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_1,
            amount=100.0,
            message="Payment Request to be updated"
        )
        collection = self.Services.with_user(user).browse(1)

        # Use service to update the payment request
        with collection.work_on("payment.request") as work:
            service = work.component(usage="payment_request")
            params = UpdatePaymentRequestParams(
                currency_uri=currency.uri,
                payment_request_id=payment_request.id,
                wallet_uri=wallet_1.uri,
                status="cancelled",
                message="Not needed anymore."
            )
            res = service.update_payment_request(
                update_payment_request_params=params
            )
            self.assertTrue(res)
            self.assertEqual(payment_request.state, "cancelled")
            self.assertEqual(payment_request.message, "Not needed anymore.")

    def test_payment_request_service_update_5(self):
        """Attempt to cancel a payment request by a wrong WALLET

        To cancel a payment request, you must :
        1. be the user that owns the creator wallet
        2. perform the cancellation from the creator wallet

        In this test, condition 2 is not met. Update should fail.
        """

        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner_1 = self._create_res_partner()
        user_1 = self._create_res_user(partner=partner_1, company=company)
        wallet_1 = self._create_res_partner_backend(partner_1, currency, ident="12345")
        partner_2 = self._create_res_partner()
        user_2 = self._create_res_user(login="jdoe2", partner=partner_2, company=company)
        wallet_2 = self._create_res_partner_backend(partner_2, currency, ident="67890")
        payment_request = self._create_payment_request(
            creator_wallet=wallet_1,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_1,
            amount=100.0,
            message="Payment Request to be updated"
        )
        collection = self.Services.with_user(user_2).browse(1)
        # Use service to update the payment request by the sender wallet
        with collection.work_on("payment.request") as work:
            service = work.component(usage="payment_request")
            params = UpdatePaymentRequestParams(
                currency_uri=currency.uri,
                payment_request_id=payment_request.id,
                wallet_uri=wallet_2.uri,
                status="cancelled",
                message="Not needed anymore."
            )
            with self.assertRaises(ValidationError) as context:
                service.update_payment_request(
                    update_payment_request_params=params
                )
            self.assertEqual(payment_request.state, "open")
            self.assertIn("Only the creator wallet can cancel the payment request", str(context.exception))

    def test_payment_request_service_update_6(self):
        """Update a payment request to "refused" status.

        To refuse a payment request, you must :
        1. be the user that owns the sender wallet
        2. perform the refusal from the sender wallet

        In this test, both conditions are met. Update should succeed.
        """
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner_1 = self._create_res_partner()
        user_1 = self._create_res_user(partner=partner_1, company=company)
        wallet_1 = self._create_res_partner_backend(partner_1, currency, ident="12345")
        partner_2 = self._create_res_partner()
        user_2 = self._create_res_user(login="jdoe2", partner=partner_2, company=company)
        wallet_2 = self._create_res_partner_backend(partner_2, currency, ident="67890")
        payment_request = self._create_payment_request(
            creator_wallet=wallet_1,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_1,
            amount=100.0,
            message="Payment Request to be refused"
        )

        collection = self.Services.with_user(user_2).browse(1)
        # Use service to update the payment request by the sender wallet
        with collection.work_on("payment.request") as work:
            service = work.component(usage="payment_request")
            params = UpdatePaymentRequestParams(
                currency_uri=currency.uri,
                payment_request_id=payment_request.id,
                wallet_uri=wallet_2.uri,
                status="refused",
                message="I refuse to pay"
            )
            res = service.update_payment_request(
                update_payment_request_params=params
            )
            self.assertTrue(res)
            self.assertEqual(payment_request.state, "refused")
            self.assertEqual(payment_request.refusal_reason, "I refuse to pay")

    def test_payment_request_service_update_7(self):
        """Attempt to refuse a payment request by a wrong WALLET

        To refuse a payment request, you must :
        1. be the user that owns the sender wallet
        2. perform the refusal from the sender wallet

        In this test, condition 2 is not met. Update should fail.
        """

        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner_1 = self._create_res_partner()
        user_1 = self._create_res_user(partner=partner_1, company=company)
        wallet_1 = self._create_res_partner_backend(partner_1, currency, ident="12345")
        partner_2 = self._create_res_partner()
        user_2 = self._create_res_user(login="jdoe2", partner=partner_2, company=company)
        wallet_2 = self._create_res_partner_backend(partner_2, currency, ident="67890")
        payment_request = self._create_payment_request(
            creator_wallet=wallet_1,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_1,
            amount=100.0,
            message="Payment Request to be refused"
        )

        collection = self.Services.with_user(user_1).browse(1)
        # Use service to update the payment request by the sender wallet
        with collection.work_on("payment.request") as work:
            service = work.component(usage="payment_request")
            params = UpdatePaymentRequestParams(
                currency_uri=currency.uri,
                payment_request_id=payment_request.id,
                wallet_uri=wallet_1.uri,
                status="refused",
                message="I refuse to pay"
            )
            with self.assertRaises(ValidationError) as context:
                service.update_payment_request(
                    update_payment_request_params=params
                )
            self.assertEqual(payment_request.state, "open")
            self.assertIn("Only the sender wallet can refuse the payment request", str(context.exception))
