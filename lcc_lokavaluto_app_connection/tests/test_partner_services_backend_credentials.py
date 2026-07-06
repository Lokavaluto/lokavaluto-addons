from odoo.addons.component.tests.common import TransactionComponentCase

class TestPartnerServiceBackendCredentials(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        ## The test asserts empty ``authorized_actions`` on fresh
        ## wallets; purge any pre-existing reconversion rules so the
        ## assertion stays deterministic regardless of DB state.
        self.env["reconversion.rule"].search([]).unlink()

        self.ResUsers = self.env["res.users"]
        self.ResPartner = self.env["res.partner"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.ResAltCurrency = self.env["res.alt.currency"]

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

        self.user_1 = self.ResUsers.create({"name": "John Doe", "login": "foo"})
        self.partner_1 = self.user_1.partner_id
        self.partner_1.public_profile_id.email = "john@doe.com"

        # Create wallets
        self.wallet_A_1 = self.ResPartnerBackend.create(
            {
                "partner_id": self.partner_1.id,
                "name": "foo:15487589688745824",
                "ident": "15487589688745824",
                "alt_currency_id": self.currencyA.id,
                "status": "active",
                "active": True,
            }
        )
        self.wallet_A_2 = self.ResPartnerBackend.create(
            {
                "partner_id": self.partner_1.id,
                "name": "foo:36fdqfldfqlkhfkqff",
                "ident": "36fdqfldfqlkhfkqff",
                "alt_currency_id": self.currencyA.id,
                "status": "active",
                "active": True,
            }
        )
        self.wallet_B_1 = self.ResPartnerBackend.create(
            {
                "partner_id": self.partner_1.id,
                "name": "foo:ugfvq;rueqv51qvrhvqr",
                "ident": "rueqv51qvrhvqr",
                "alt_currency_id": self.currencyB.id,
                "status": "active",
                "active": True,
            }
        )
        self.wallet_B_2 = self.ResPartnerBackend.create(
            {
                "partner_id": self.partner_1.id,
                "name": "foo:tdfdsvqj656fdferf56vlrjq",
                "ident": "tdfdsvqj656fdferf56vlrjq",
                "alt_currency_id": self.currencyB.id,
                "status": "active",
                "active": True,
            }
        )


    def test_backend_credentials(self):
        collection = (
            self.env["lokavaluto.private.services"]
            .with_user(self.user_1)
            .browse(1)
        )
        currency_A_backend_key = f"{self.currencyA.engine}:{self.currencyA.ident}"
        currency_B_backend_key = f"{self.currencyB.engine}:{self.currencyB.ident}"
        with collection.work_on("res.partner.backend") as work:
            # Notice : I did not understand which model I should put in work_on() argument
            service = work.component(usage="partner")
            result = service.backend_credentials()

            expected_result = [
                {
                    "type": "foo:currencyA",
                    "accounts": [
                        {
                            "wallet_uri": "foo://currencyA/wallet/15487589688745824",
                            "active": True,
                            "is_topup_allowed": True,
                            "is_payment_request_allowed": False,
                            "auth_context": {},
                            "authorized_actions": [],
                        },
                        {
                            "wallet_uri": "foo://currencyA/wallet/36fdqfldfqlkhfkqff",
                            "active": True,
                            "is_topup_allowed": True,
                            "is_payment_request_allowed": False,
                            "auth_context": {},
                            "authorized_actions": [],
                        },
                    ],
                    "min_credit_amount": 0,
                    "max_credit_amount": 0,
                },
                {
                    "type": "foo:currencyB",
                    "accounts": [
                        {
                            "wallet_uri": "foo://currencyB/wallet/rueqv51qvrhvqr",
                            "active": True,
                            "is_topup_allowed": True,
                            "is_payment_request_allowed": False,
                            "auth_context": {},
                            "authorized_actions": [],
                        },
                        {
                            "wallet_uri": "foo://currencyB/wallet/tdfdsvqj656fdferf56vlrjq",
                            "active": True,
                            "is_topup_allowed": True,
                            "is_payment_request_allowed": False,
                            "auth_context": {},
                            "authorized_actions": [],
                        },
                    ],
                    "min_credit_amount": 0,
                    "max_credit_amount": 0,
                },
            ]

            self.assertEqual(result, expected_result)

    def test_backend_credentials_auth_fields_present(self):
        """Each account entry includes auth_context and authorized_actions."""
        result = self.partner_1.get_partner_wallets_credentials()
        for currency_data in result:
            for account in currency_data["accounts"]:
                self.assertIn("auth_context", account)
                self.assertIn("authorized_actions", account)
                self.assertIsInstance(account["auth_context"], dict)
                self.assertIsInstance(account["authorized_actions"], list)
