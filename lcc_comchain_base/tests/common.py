from types import SimpleNamespace

from minimock import Mock

from odoo.addons.component.tests.common import TransactionComponentCase



class ComchainTestCase(TransactionComponentCase):
    """Shared test base for comchain service tests.

    Sets up a comchain currency and provides helpers to create users,
    wallets, and call service endpoints with mocked request headers.
    """

    def setUp(self):
        super().setUp()
        currency_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        self.comchain_currency = self.env["res.alt.currency"].create(
            {
                "name": "Test Comchain",
                "ident": "testcomchain",
                "active": True,
                "engine": "comchain",
                "currency_unit_product_id": currency_product.id,
            }
        )

    ## User / wallet helpers

    def _make_user_and_wallet(self, login, comchain_type="0", addr="0xabc"):
        """Create a user and associated comchain wallet."""
        user = self._make_users(login)
        user_uri = self._user_uri(addr)
        wallet = self._make_comchain_wallet(
            user, comchain_type=comchain_type, addr=addr
        )
        return SimpleNamespace(
            user=user,
            user_uri=user_uri,
            user_ident=wallet.ident,
            wallet=wallet,
        )

    def _make_users(self, *logins):
        users = []
        for login in logins:
            user = self.env["res.users"].create(
                {"name": login.capitalize(), "login": login}
            )
            users.append(user)
        return users[0] if len(logins) == 1 else users

    def _make_comchain_wallet(self, user, comchain_type="0", addr="0xabc"):
        return self.env["res.partner.backend"].create(
            {
                "partner_id": user.partner_id.id,
                "name": f"comchain:{addr}",
                "ident": addr,
                "alt_currency_id": self.comchain_currency.id,
                "comchain_type": comchain_type,
                "comchain_status": "active",
            }
        )

    def _user_uri(self, addr):
        """Build a user_uri for the given user on the test currency."""
        return f"comchain://testcomchain/user/{addr}"

    ## Service helpers

    def _get_wallet_service(self, user):
        collection = self.env["lokavaluto.private.services"].with_user(user).browse(1)
        with collection.work_on("res.partner.backend") as work:
            return work.component(usage="wallet")

    def _get_recipient_service(self, user):
        collection = self.env["lokavaluto.private.services"].with_user(user).browse(1)
        with collection.work_on("res.partner.backend") as work:
            return work.component(usage="recipient")

    ## Mock request helper

    def _mock_request(self, caller, features_header=None):
        """Build a mock request with caller's auth header."""
        headers = {"X-Lokapi-Caller-User-Uri": caller.user_uri}
        if features_header:
            headers["X-Client-Features"] = features_header
        return Mock(
            "request",
            httprequest=Mock("httprequest", headers=headers),
            future_response=Mock("future_response", headers={}),
            _common_features=None,
        )
