from odoo.addons.component.tests.common import TransactionComponentCase
from ..datamodel.partner_info import (
    PartnerCreditRequestsGetParam,
    PartnerValidateCreditRequest,
)


class TestPartnerServiceCreditRequests(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        self.ResUsers = self.env["res.users"]
        self.ResPartner = self.env["res.partner"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.ResAltCurrency = self.env["res.alt.currency"]
        self.CreditRequest = self.env["credit.request"]

        self.currency_unit_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        self.currencyA = self.ResAltCurrency.create(
            {
                "name": "Currency A",
                "ident": "currencyA",
                "active": True,
                "engine": "foo",
                "currency_unit_product_id": self.currency_unit_product.id,
            }
        )
        self.currencyB = self.ResAltCurrency.create(
            {
                "name": "Currency B",
                "ident": "currencyB",
                "active": True,
                "engine": "foo",
                "currency_unit_product_id": self.currency_unit_product.id,
            }
        )

        self.user = self.ResUsers.create({"name": "John Doe", "login": "foo"})
        self.user_admin = self.ResUsers.create(
            {
                "name": "User Admin",
                "login": "user_admin",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref(
                                "lcc_lokavaluto_app_connection.group_wallet_full_manager"
                            ).id
                        ],
                    )
                ],
            }
        )
        self.partner = self.user.partner_id

        self.wallet = self.ResPartnerBackend.create(
            {
                "partner_id": self.partner.id,
                "name": "foo:15487589688745824",
                "ident": "15487589688745824",
                "alt_currency_id": self.currencyA.id,
            }
        )

        self.credit_request_A = self.CreditRequest.create(
            {
                "wallet_id": self.wallet.id,
                "amount": 15.00,
                "state": "open",
            }
        )
        self.credit_request_B = self.CreditRequest.create(
            {
                "wallet_id": self.wallet.id,
                "amount": 20.00,
                "state": "open",
            }
        )
        self.credit_request_C = self.CreditRequest.sudo().create(
            {
                "wallet_id": self.wallet.id,
                "amount": 32.00,
                "state": "open",
            }
        )
        self.credit_request_D = self.CreditRequest.create(
            {
                "wallet_id": self.wallet.id,
                "amount": 45.00,
                "state": "error",
            }
        )
        self.credit_request_E = self.CreditRequest.create(
            {
                "wallet_id": self.wallet.id,
                "amount": 33.00,
                "state": "pending",
            }
        )
        self.credit_request_F = self.CreditRequest.create(
            {
                "wallet_id": self.wallet.id,
                "amount": 56.00,
                "state": "pending",
            }
        )

    def test_credit_requests_service(self):
        collection = (
            self.env["lokavaluto.private.services"].with_user(self.user).browse(1)
        )
        sender_credit_request_get_params = PartnerCreditRequestsGetParam(
            backend_keys=[
                f"{self.currencyA.engine}:{self.currencyA.ident}",
                "toto:tata",
            ]
        )
        with collection.work_on("res.partner.backend") as work:
            # Notice : I did not understand which model I should put in work_on() argument
            service = work.component(usage="partner")
            result = service.credit_requests(
                partner_credit_requests_get_param=sender_credit_request_get_params
            )

            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["amount"], 56.00)
            self.assertTrue(result[0]["paid"])

    # def test_pending_topup(self):
    #     collection = (
    #         self.env["lokavaluto.private.services"]
    #         .with_user(self.user)
    #         .browse(1)
    #     )
    #     pending_topup_get_params = {
    #         "backend_keys": "foo:15487589688745824"
    #     }
    #     with collection.work_on("res.partner.backend") as work:
    #         # Notice : I did not understand which model I should put in work_on() argument
    #         service = work.component(usage="partner")
    #         result = service.pending_topup()

    #         self.assertEqual(len(result), 1)
    #         self.assertEqual(result[0]["amount"], 33.00)
    #         self.assertTrue(result[0]["paid"])

    # def test_remove_pending_topup(self):
    #     collection = (
    #         self.env["lokavaluto.private.services"]
    #         .with_user(self.user)
    #         .browse(1)
    #     )

    #     with collection.work_on("res.partner.backend") as work:
    #         # Notice : I did not understand which model I should put in work_on() argument
    #         service = work.component(usage="partner")
    #         result = service.remove_pending_topup()

    #         self.assertTrue(result)
    #         self.assertEqual(self.credit_request_E, None)

    def test_validate_credit_request_service(self):
        collection = (
            self.env["lokavaluto.private.services"].with_user(self.user_admin).browse(1)
        )
        validate_credit_request_get_params = PartnerValidateCreditRequest(
            ids=[self.credit_request_F.id]
        )
        with collection.work_on("res.partner.backend") as work:
            # Notice : I did not understand which model I should put in work_on() argument
            service = work.component(usage="partner")
            result = service.validate_credit_requests(
                validate_credit_request_get_params
            )

            self.assertTrue(result)
            self.assertEqual(self.credit_request_F.state, "done")
