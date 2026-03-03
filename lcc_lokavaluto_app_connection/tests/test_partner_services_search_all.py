from odoo.exceptions import AccessDenied
from odoo.addons.component.tests.common import TransactionComponentCase
from ..datamodel.partner_info import PartnerSearchInfo


class TestPartnerServiceSearchAllRecipients(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        currency_unit_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        self.currencyA = self.env["res.alt.currency"].create(
            {
                "name": "Currency A",
                "ident": "currencyA",
                "active": True,
                "engine": "foo",
                "currency_unit_product_id": currency_unit_product.id,
            }
        )

    ## Helpers

    def _make_users(self, *logins):
        users = []
        for login in logins:
            user = self.env["res.users"].create(
                {"name": login.capitalize(), "login": login}
            )
            self.env["res.partner.backend"].create(
                {
                    "partner_id": user.partner_id.id,
                    "name": f"foo:{login}",
                    "ident": login,
                    "alt_currency_id": self.currencyA.id,
                    "status": "active",
                }
            )
            users.append(user)
        return users[0] if len(logins) == 1 else users

    def _set_admin(self, user):
        admin_group = self.env.ref(
            "lcc_lokavaluto_app_connection.group_wallet_accounts_manager"
        )
        user.groups_id = [(4, admin_group.id)]

    def _get_service_as_user(self, user):
        collection = self.env["lokavaluto.private.services"].with_user(user).browse(1)
        with collection.work_on("res.partner.backend") as work:
            return work.component(usage="partner")

    def _make_search_params(self, value="", backend_keys=None):
        if backend_keys is None:
            backend_keys = [f"{self.currencyA.engine}:{self.currencyA.ident}"]
        return PartnerSearchInfo(
            value=value,
            backend_keys=backend_keys,
            offset=0,
            limit=30,
            order="name asc",
        )

    ## Tests

    def test_can_search_all_recipients_as_accounts_manager(self):
        """A user with group_wallet_accounts_manager can search all recipients."""

        charlie = self._make_users("charlie")
        self._set_admin(charlie)
        service = self._get_service_as_user(charlie)

        self.assertTrue(service.can_search_all_recipients())

    def test_can_search_all_recipients_as_regular_user(self):
        """A user without group_wallet_accounts_manager cannot search all recipients."""

        alice = self._make_users("alice")
        service = self._get_service_as_user(alice)

        self.assertFalse(service.can_search_all_recipients())

    def test_non_admin_user_gets_access_denied(self):
        """A user without group_wallet_accounts_manager must get AccessDenied."""

        alice = self._make_users("alice")
        service = self._get_service_as_user(alice)
        search_params = self._make_search_params(value="whatever")

        with self.assertRaises(AccessDenied):
            service.search_all_recipients(recipients_search_info=search_params)

    def test_admin_can_see_themselves_in_results(self):
        """Unlike search_recipients, search_all must include the caller."""

        charlie = self._make_users("charlie")
        self._set_admin(charlie)
        service = self._get_service_as_user(charlie)
        search_params = self._make_search_params(value="charlie")

        result = service.search_all_recipients(recipients_search_info=search_params)

        result_ids = {row["id"] for row in result["rows"]}
        self.assertIn(charlie.partner_id.id, result_ids)

    def test_admin_sees_recipients_despite_restriction_rules(self):
        """Wallet restriction rules must NOT filter search_all results."""

        charlie, alice, bob = self._make_users("charlie", "alice", "bob")
        self._set_admin(charlie)

        # Restriction rule only allows bob's wallet as recipient for charlie
        self.env["wallet.restriction.rule"].create(
            {
                "name": "Restrictive Rule",
                "active": True,
                "sender_wallet_domain": "[('name', '=', 'foo:charlie')]",
                "recipient_wallet_domain": "[('name', '=', 'foo:bob')]",
            }
        )

        service = self._get_service_as_user(charlie)
        # Non-empty value to trigger full search (empty returns favorites only)
        search_params = self._make_search_params(value="li")
        search_params.sender_wallet_ident = "foo:charlie"

        # Prove the rule actually restricts in search_recipients:
        # alice should be blocked (only bob's wallet is allowed)
        result = service.search_recipients(recipients_search_info=search_params)

        restricted_ids = {row["id"] for row in result["rows"]}
        self.assertNotIn(alice.partner_id.id, restricted_ids)

        # Now prove search_all ignores the restriction rule:
        # Both charlie and alice must appear
        result = service.search_all_recipients(recipients_search_info=search_params)

        all_ids = {row["id"] for row in result["rows"]}
        self.assertIn(alice.partner_id.id, all_ids)
        self.assertIn(charlie.partner_id.id, all_ids)
