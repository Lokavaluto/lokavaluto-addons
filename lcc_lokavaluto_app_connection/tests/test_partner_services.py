from odoo.addons.component.tests.common import TransactionComponentCase


class TestPartnerService(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        self.ResUsers = self.env["res.users"]
        self.ResPartner = self.env["res.partner"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.WalletRestrictionRule = self.env["wallet.restriction.rule"]

        self.sender_user = self.ResUsers.create({"name": "Sender", "login": "foo"})
        self.sender = self.ResPartner.create(
            {"name": "Sender", "user_id": self.sender_user.id}
        )
        self.sender_wallet = self.ResPartnerBackend.create(
            {
                "partner_id": self.sender.id,
                "name": "comchain:sender",
                "type": "comchain",
            }
        )

        self.recipient_allowed = self.ResPartner.create({"name": "Allowed Recipient"})
        self.recipient_allowed_wallet = self.ResPartnerBackend.create(
            {
                "partner_id": self.recipient_allowed.id,
                "name": "comchain:allowed_recipient",
                "type": "comchain",
            }
        )
        self.recipient_not_allowed = self.ResPartner.create(
            {"name": "Not Allowed Recipient"}
        )
        self.recipient_not_allowed_wallet = self.ResPartnerBackend.create(
            {
                "partner_id": self.recipient_not_allowed.id,
                "name": "comchain:not_allowed_recipient",
                "type": "comchain",
            }
        )

        self.PartnerCheckTransactionGetParams = self.env.datamodels[
            "partner.check.transaction.get.params"
        ]
        self.sender_to_allowed_recipient_get_params = (
            self.PartnerCheckTransactionGetParams(
                sender_wallet_ident=self.sender_wallet.name,
                recipient_wallet_ident=self.recipient_allowed_wallet.name,
            )
        )

        self.sender_to_not_allowed_recipient_get_params = (
            self.PartnerCheckTransactionGetParams(
                sender_wallet_ident=self.sender_wallet.name,
                recipient_wallet_ident=self.recipient_not_allowed_wallet.name,
            )
        )

    def test_is_transaction_allowed(self):
        self.WalletRestrictionRule.create(
            {
                "name": "Test Rule",
                "sender_wallet_domain": "[('name', '=', 'comchain:sender')]",
                "recipient_wallet_domain": "[('name', '=', 'comchain:allowed_recipient')]",
            }
        )
        collection = (
            self.env["lokavaluto.private.services"]
            .with_user(self.sender_user)
            .browse(1)
        )
        with collection.work_on("res.partner.backend") as work:
            # Notice : I did not understand which model I should put in work_on() argument
            service = work.component(usage="partner")
            result = service.is_transaction_allowed(
                partner_is_transaction_allowed_get_params=self.sender_to_allowed_recipient_get_params
            )
            self.assertTrue(result)
            result = service.is_transaction_allowed(
                partner_is_transaction_allowed_get_params=self.sender_to_not_allowed_recipient_get_params
            )
            self.assertFalse(result)

    def test_check_transaction_is_always_allowed_if_no_rule_found(self):
        collection = (
            self.env["lokavaluto.private.services"]
            .with_user(self.sender_user)
            .browse(1)
        )
        with collection.work_on("res.partner.backend") as work:
            service = work.component(usage="partner")
            result = service.is_transaction_allowed(
                partner_is_transaction_allowed_get_params=self.sender_to_allowed_recipient_get_params
            )
            self.assertTrue(result)
            result = service.is_transaction_allowed(
                partner_is_transaction_allowed_get_params=self.sender_to_not_allowed_recipient_get_params
            )
            self.assertTrue(result)

    def test_only_first_matching_rule_is_applied(self):
        rule = self.WalletRestrictionRule.create(
            {
                "name": "Test Rule",
                "sender_wallet_domain": "[('name', '=', 'comchain:sender')]",
                "recipient_wallet_domain": "[('name', '=', 'comchain:allowed_recipient')]",
            }
        )
        first_matching_rule = self.WalletRestrictionRule.create(
            {
                "sequence": rule.sequence - 1,
                "name": "First Matching Rule",
                "sender_wallet_domain": "[('name', '=', 'comchain:sender')]",
                "recipient_wallet_domain": "[('name', '=', 'comchain:not_allowed_recipient')]",
                # Notice that in this test we allow the Not Allowed Recipient
            }
        )

        collection = (
            self.env["lokavaluto.private.services"]
            .with_user(self.sender_user)
            .browse(1)
        )
        with collection.work_on("res.partner.backend") as work:
            service = work.component(usage="partner")
            result = service.is_transaction_allowed(
                partner_is_transaction_allowed_get_params=self.sender_to_allowed_recipient_get_params
            )
            self.assertFalse(result)
            result = service.is_transaction_allowed(
                partner_is_transaction_allowed_get_params=self.sender_to_not_allowed_recipient_get_params
            )
            self.assertTrue(result)

    def test_rule_allowing_all_senders(self):
        self.WalletRestrictionRule.create(
            {
                "name": "Test Rule",
                "sender_wallet_domain": "[]",
                "recipient_wallet_domain": "[('name', '=', 'comchain:allowed_recipient')]",
            }
        )

        collection = (
            self.env["lokavaluto.private.services"]
            .with_user(self.sender_user)
            .browse(1)
        )
        with collection.work_on("res.partner.backend") as work:
            service = work.component(usage="partner")
            result = service.is_transaction_allowed(
                partner_is_transaction_allowed_get_params=self.sender_to_allowed_recipient_get_params
            )
            self.assertTrue(result)
            result = service.is_transaction_allowed(
                partner_is_transaction_allowed_get_params=self.sender_to_not_allowed_recipient_get_params
            )
            self.assertFalse(result)

        another_sender_user = self.ResUsers.create(
            {"name": "Another Sender", "login": "bar"}
        )
        another_sender = self.ResPartner.create(
            {"name": "Another Sender", "user_id": another_sender_user.id}
        )
        another_sender_wallet = self.ResPartnerBackend.create(
            {
                "partner_id": another_sender.id,
                "name": "comchain:anothersender",
                "type": "comchain",
            }
        )

        another_sender_to_allowed_recipient_get_params = (
            self.PartnerCheckTransactionGetParams(
                sender_wallet_ident=another_sender_wallet.name,
                recipient_wallet_ident=self.recipient_allowed_wallet.name,
            )
        )
        another_sender_to_not_allowed_recipient_get_params = (
            self.PartnerCheckTransactionGetParams(
                sender_wallet_ident=another_sender_wallet.name,
                recipient_wallet_ident=self.recipient_not_allowed_wallet.name,
            )
        )

        collection = (
            self.env["lokavaluto.private.services"]
            .with_user(another_sender_user)
            .browse(1)
        )
        with collection.work_on("res.partner.backend") as work:
            service = work.component(usage="partner")
            result = service.is_transaction_allowed(
                partner_is_transaction_allowed_get_params=another_sender_to_allowed_recipient_get_params
            )
            self.assertTrue(result)
            result = service.is_transaction_allowed(
                partner_is_transaction_allowed_get_params=another_sender_to_not_allowed_recipient_get_params
            )
            self.assertFalse(result)
