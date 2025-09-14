from odoo.addons.component.tests.common import TransactionComponentCase
from ..datamodel.partner_info import PartnerSearchInfo

class TestPartnerServiceSearchRecipients(TransactionComponentCase):
    def setUp(self):
        super().setUp()

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
        self.user_2 = self.ResUsers.create({"name": "Tintin", "login": "tintin"})
        self.partner_2 = self.user_2.partner_id
        self.partner_2.public_profile_id.email = "tintin@herge.be"
        self.user_3 = self.ResUsers.create({"name": "Capitaine Haddock", "login": "haddock"})
        self.partner_3 = self.user_3.partner_id
        self.partner_3.public_profile_id.email = "haddock@herge.be"

        # Create wallets
        self.wallet_A_1 = self.ResPartnerBackend.create(
            {
                "partner_id": self.partner_1.id,
                "name": "foo:15487589688745824",
                "ident": "15487589688745824",
                "alt_currency_id": self.currencyA.id,
                "status": "active",
            }
        )
        self.wallet_A_2 = self.ResPartnerBackend.create(
            {
                "partner_id": self.partner_2.id,
                "name": "foo:36fdqfldfqlkhfkqff",
                "ident": "36fdqfldfqlkhfkqff",
                "alt_currency_id": self.currencyA.id,
                "status": "active",
            }
        )
        self.wallet_A_3 = self.ResPartnerBackend.create(
            {
                "partner_id": self.partner_3.id,
                "name": "foo:fdn:qjdnq5f4qfjk",
                "ident": "qjdnq5f4qfjk",
                "alt_currency_id": self.currencyA.id,
                "status": "active",
            }
        )
        self.wallet_B_1 = self.ResPartnerBackend.create(
            {
                "partner_id": self.partner_1.id,
                "name": "foo:ugfvq;rueqv51qvrhvqr",
                "ident": "rueqv51qvrhvqr",
                "alt_currency_id": self.currencyB.id,
                "status": "active",
            }
        )
        self.wallet_B_2 = self.ResPartnerBackend.create(
            {
                "partner_id": self.partner_2.id,
                "name": "foo:tdfdsvqj656fdferf56vlrjq",
                "ident": "tdfdsvqj656fdferf56vlrjq",
                "alt_currency_id": self.currencyB.id,
                "status": "active",
            }
        )
        self.wallet_B_3 = self.ResPartnerBackend.create(
            {
                "partner_id": self.partner_3.id,
                "name": "foo:oaeuhf3ef6zfhlqr65fqs",
                "ident": "oaeuhf3ef6zfhlqr65fqs",
                "alt_currency_id": self.currencyB.id,
                "status": "active",
            }
        )




    def test_search_one_recipient(self):
        collection = (
            self.env["lokavaluto.private.services"]
            .with_user(self.user_1)
            .browse(1)
        )
        currency_A_backend_key = f"{self.currencyA.engine}:{self.currencyA.ident}"
        search_get_params = PartnerSearchInfo(
            value = "tintin",
            backend_keys = [currency_A_backend_key],
            offset = 0,
            limit = 30,
            order= "is_favorite desc name",
            sender_wallet_ident = self.wallet_A_1.name,
        )
        with collection.work_on("res.partner.backend") as work:
            # Notice : I did not understand which model I should put in work_on() argument
            service = work.component(usage="partner")
            result = service.search_recipients(
                recipients_search_info=search_get_params
            )

            self.assertEqual(result.get("count", False), 1)
            self.assertTrue(result.get("rows", False))
            row_1 = result["rows"][0]
            self.assertEqual(row_1.get("name", False), "Tintin")
            self.assertTrue(row_1.get("monujo_backends", False))
            row_1_monujo_backends = row_1["monujo_backends"]
            self.assertTrue(row_1_monujo_backends.get(currency_A_backend_key, False))
            monujo_backend_1 = row_1_monujo_backends[currency_A_backend_key][0]
            self.assertEqual(monujo_backend_1, self.wallet_A_2.ident)


    def test_search_two_recipients(self):
        collection = (
            self.env["lokavaluto.private.services"]
            .with_user(self.user_1)
            .browse(1)
        )
        currency_A_backend_key = f"{self.currencyA.engine}:{self.currencyA.ident}"
        search_get_params = PartnerSearchInfo(
            value = "herge",
            backend_keys = [currency_A_backend_key],
            offset = 0,
            limit = 30,
            order= "is_favorite desc name",
            sender_wallet_ident = self.wallet_A_1.name,
        )
        with collection.work_on("res.partner.backend") as work:
            # Notice : I did not understand which model I should put in work_on() argument
            service = work.component(usage="partner")
            result = service.search_recipients(
                recipients_search_info=search_get_params
            )

            self.assertEqual(result.get("count", False), 2)
            self.assertTrue(result.get("rows", False))

            # Checks first row
            row_1 = result["rows"][0]
            self.assertEqual(row_1.get("name", False), "Tintin")
            self.assertTrue(row_1.get("monujo_backends", False))
            row_1_monujo_backends = row_1["monujo_backends"]
            self.assertTrue(row_1_monujo_backends.get(currency_A_backend_key, False))
            monujo_backend_1 = row_1_monujo_backends[currency_A_backend_key][0]
            self.assertEqual(monujo_backend_1, self.wallet_A_2.ident)

            # Checks second row
            row_2 = result["rows"][1]
            self.assertEqual(row_2.get("name", False), "Capitaine Haddock")
            self.assertTrue(row_2.get("monujo_backends", False))
            row_2_monujo_backends = row_2["monujo_backends"]
            self.assertTrue(row_2_monujo_backends.get(currency_A_backend_key, False))
            monujo_backend_2 = row_2_monujo_backends[currency_A_backend_key][0]
            self.assertEqual(monujo_backend_2, self.wallet_A_3.ident)
