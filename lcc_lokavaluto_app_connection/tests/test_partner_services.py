from odoo.addons.component.tests.common import TransactionComponentCase


class TestPartnerService(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        self.ResUsers = self.env["res.users"]
        self.ResPartner = self.env["res.partner"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.WalletRestrictionRule = self.env["wallet.restriction.rule"]

        self.senderUser = self.ResUsers.create({"name": "Sender", "login": "foo"})
        self.sender = self.ResPartner.create({"name": "Sender", "user_id": self.senderUser.id})
        self.sender_wallet = self.ResPartnerBackend.create({
            "partner_id": self.sender.id,
            "name": "Sender",
            "type": "foo"
        })

        self.recipient_allowed = self.ResPartner.create({"name": "Allowed Recipient"})
        self.recipient_allowed_wallet = self.ResPartnerBackend.create({
            "partner_id": self.recipient_allowed.id,
            "name": "Allowed Recipient",
            "type": "foo"
        })
        self.recipient_not_allowed = self.ResPartner.create({"name": "Not Allowed Recipient"})
        self.recipient_not_allowed_wallet = self.ResPartnerBackend.create({
            "partner_id": self.recipient_not_allowed.id,
            "name": "Not Allowed Recipient",
            "type": "foo"
        })

        self.rule = self.WalletRestrictionRule.create({
            "name": "Test Rule",
            "sender_wallet_domain": "[('name', '=', 'Sender')]",
            "recipient_wallet_domain": "[('name', '=', 'Allowed Recipient')]"
        })

    def test_check_that_transaction_is_allowed(self):
        collection = self.env["lokavaluto.private.services"].with_user(self.senderUser).browse(1)
        with collection.work_on("res.partner.backend") as work:
            # Notice : I did not understand which model I should put in work_on() argument
            service = work.component(usage="partner")
            result = service.check_that_transaction_is_allowed(_id=self.recipient_allowed.id)
            self.assertTrue(result)
            result = service.check_that_transaction_is_allowed(_id=self.recipient_not_allowed.id)
            self.assertFalse(result)

    def test_check_transaction_is_always_allowed_if_no_rule_found(self):
        sender_without_matching_rule = self.ResUsers.create({"name": "senderWithoutRule", "login": "bar"})

        collection = self.env["lokavaluto.private.services"].with_user(sender_without_matching_rule).browse(1)
        with collection.work_on("res.partner.backend") as work:
            service = work.component(usage="partner")
            result = service.check_that_transaction_is_allowed(_id=self.recipient_allowed.id)
            self.assertTrue(result)
            result = service.check_that_transaction_is_allowed(_id=self.recipient_not_allowed.id)
            self.assertTrue(result)

    def test_only_first_matching_rule_is_applied(self):
        first_matching_rule = self.WalletRestrictionRule.create({
            "sequence": self.rule.sequence - 1,
            "name": "First Matching Rule",
            "sender_wallet_domain": "[('name', '=', 'Sender')]",
            "recipient_wallet_domain": "[('name', '=', 'Not Allowed Recipient')]"
            # Notice that in this test we allow the Not Allowed Recipient
        })

        collection = self.env["lokavaluto.private.services"].with_user(self.senderUser).browse(1)
        with collection.work_on("res.partner.backend") as work:
            service = work.component(usage="partner")
            result = service.check_that_transaction_is_allowed(_id=self.recipient_allowed.id)
            self.assertFalse(result)
            result = service.check_that_transaction_is_allowed(_id=self.recipient_not_allowed.id)
            self.assertTrue(result)
