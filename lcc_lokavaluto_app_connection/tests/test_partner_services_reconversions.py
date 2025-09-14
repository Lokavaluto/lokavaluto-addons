from odoo.addons.component.tests.common import TransactionComponentCase
from ..datamodel.partner_info import PartnerReconversions

class TestPartnerServiceReconversions(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        self.ResUsers = self.env["res.users"]
        self.ResPartner = self.env["res.partner"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.ResAltCurrency = self.env["res.alt.currency"]
        self.DebitRequest = self.env["debit.request"]

        self.currency_unit_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        self.currency__product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        self.currencyA = self.ResAltCurrency.create(
            {
                "name": "Currency A",
                "ident": "currencyA",
                "active": True,
                "engine": "foo",
                "currency_unit_product_id": self.currency_unit_product.id
            }
        )
        self.currencyB = self.ResAltCurrency.create(
            {
                "name": "Currency B",
                "ident": "currencyB",
                "active": True,
                "engine": "foo",
                "currency_unit_product_id": self.currency_unit_product.id
            }
        )

        self.user = self.ResUsers.create({"name": "John Doe", "login": "foo"})
        self.partner = self.user.partner_id

        # Create wallets
        self.wallet_A = self.ResPartnerBackend.create(
            {
                "partner_id": self.partner.id,
                "name": "foo:15487589688745824",
                "ident": "15487589688745824",
                "alt_currency_id": self.currencyA.id,
            }
        )
        self.wallet_B = self.ResPartnerBackend.create(
            {
                "partner_id": self.partner.id,
                "name": "foo:3654fsrfkhsjfh6s5qe4",
                "alt_currency_id": self.currencyB.id,
            }
        )

        # Create Debit Requests
        self.debit_request_A = self.DebitRequest.create(
            {
                "wallet_id": self.wallet_A.id,
                "amount": 15.00,
                "state": "draft",
                "transaction_id": "fdqfg1re6g5dfq1g3df54qgfd6q5g4fdg",
                "backend_ident": "foo://currencyA"
            }
        )
        self.ident_debit_request_A = f"{self.currencyA.engine}://{self.currencyA.ident}/tx/{self.debit_request_A.transaction_id}"
        self.debit_request_B = self.DebitRequest.create(
            {
                "wallet_id": self.wallet_A.id,
                "amount": 32.00,
                "state": "draft",
                "transaction_id": "fqgfqg456q8g7f465qgq684vrq5rq468",
                "backend_ident": "foo://currencyA"
            }
        )
        self.debit_request_B.state = "invoiced"
        self.ident_debit_request_B = f"{self.currencyA.engine}://{self.currencyA.ident}/tx/{self.debit_request_B.transaction_id}"
        self.debit_request_C = self.DebitRequest.create(
            {
                "wallet_id": self.wallet_A.id,
                "amount": 131.00,
                "state": "draft",
                "transaction_id": "fqmgjlfkqnlljfmq5f468545",
                "backend_ident": "foo://currencyA"
            }
        )
        self.debit_request_C.state = "paid"
        self.ident_debit_request_C = f"{self.currencyA.engine}://{self.currencyA.ident}/tx/{self.debit_request_C.transaction_id}"
        self.debit_request_D = self.DebitRequest.create(
            {
                "wallet_id": self.wallet_A.id,
                "amount": 24.00,
                "state": "draft",
                "transaction_id": "pojrlhjqh654fdKHLJDE",
                "backend_ident": "foo://currencyA"
            }
        )
        self.debit_request_D.state = "cancelled"
        self.ident_debit_request_D = f"{self.currencyA.engine}://{self.currencyA.ident}/tx/{self.debit_request_D.transaction_id}"
        self.debit_request_E = self.DebitRequest.create(
            {
                "wallet_id": self.wallet_A.id,
                "amount": 75.00,
                "state": "draft",
                "transaction_id": "piuaeifgkdhsbclvqrk48qfqlk",
                "backend_ident": "foo://currencyA"
            }
        )
        self.ident_debit_request_E = f"{self.currencyA.engine}://{self.currencyA.ident}/tx/{self.debit_request_E.transaction_id}"
        self.debit_request_F = self.DebitRequest.create(
            {
                "wallet_id": self.wallet_B.id,
                "amount": 251.00,
                "state": "draft",
                "transaction_id": "flkjqegf684f5q4g6r8",
                "backend_ident": "foo://currencyB"
            }
        )
        self.ident_debit_request_F = f"{self.currencyB.engine}://{self.currencyB.ident}/tx/{self.debit_request_F.transaction_id}"


    def test_reconversions(self):
        collection = (
            self.env["lokavaluto.private.services"]
            .with_user(self.user)
            .browse(1)
        )
        reconversions_get_params = PartnerReconversions(
            transactions=[
                self.ident_debit_request_A,
                self.ident_debit_request_B,
                self.ident_debit_request_C,
                self.ident_debit_request_D,
                self.ident_debit_request_F
            ]
        )
        with collection.work_on("res.partner.backend") as work:
            # Notice : I did not understand which model I should put in work_on() argument
            service = work.component(usage="partner")
            result = service.reconversions(
                params=reconversions_get_params
            )
            self.assertEqual(result[self.ident_debit_request_A], "received")
            self.assertEqual(result[self.ident_debit_request_B], "invoiced")
            self.assertEqual(result[self.ident_debit_request_C], "paid")
            self.assertEqual(result[self.ident_debit_request_D], "cancelled")
            self.assertEqual(result[self.ident_debit_request_F], "received")
            self.assertFalse(result.get(self.ident_debit_request_E, False))
