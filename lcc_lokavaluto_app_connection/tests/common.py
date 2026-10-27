from contextlib import contextmanager
from unittest.mock import patch

from minimock import Mock

import odoo.addons.lcc_lokavaluto_app_connection.services as lcc_services

CALLER_USER_URI_HEADER = "X-Lokapi-Caller-User-Uri"


@contextmanager
def lcc_api_caller(wallet):
    """Bind a fake HTTP request whose caller is the owner of ``wallet``.

    ``@lcc_api`` endpoints identify their caller from the
    ``X-Lokapi-Caller-User-Uri`` header of the current HTTP request.
    A test calling such an endpoint directly has no request bound,
    so this binds one carrying the user URI of ``wallet``.
    """
    user_uri = wallet.uri.replace("/wallet/", "/user/", 1)
    mock_request = Mock(
        "request",
        httprequest=Mock("httprequest", headers={CALLER_USER_URI_HEADER: user_uri}),
        future_response=Mock("future_response", headers={}),
        _common_features=None,
    )
    with patch.object(lcc_services, "request", mock_request):
        yield


class WalletContactTestMixin:
    """Shared scenarios for backend contact endpoints.

    Subclasses provide wallet_type, identifier_field, contact_params_class,
    and address, and inherit TransactionComponentCase.
    """

    def setUp(self):
        super().setUp()
        product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        )
        self.currency = self.env["res.alt.currency"].create({
            "name": "Contact test currency",
            "ident": "contact-test",
            "engine": self.wallet_type,
            "currency_unit_product_id": product.id,
        })
        self.owner = self.env["res.users"].create({
            "name": "Contact Owner",
            "login": f"{self.wallet_type}-contact-owner",
            "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
        })
        self.other_owner = self.env["res.users"].create({
            "name": "Other Contact Owner",
            "login": f"{self.wallet_type}-other-contact-owner",
        })

    def _make_wallet(self, owner, active=True, address=None):
        address = address or self.address
        return self.env["res.partner.backend"].create({
            "name": f"{self.wallet_type}:{address}",
            "alt_currency_id": self.currency.id,
            "partner_id": owner.partner_id.id,
            "ident": address,
            self.identifier_field: address,
            "active": active,
        })

    def _contact(self, addresses):
        collection = (
            self.env["lokavaluto.private.services"].with_user(self.owner).browse(1)
        )
        with collection.work_on("res.partner.backend") as work:
            service = work.component(usage=self.wallet_type)
            return service.contact(self.contact_params_class(addresses=addresses))

    def _assert_owner(self, result, owner):
        self.assertTrue(owner.partner_id.public_name)
        self.assertEqual(result[self.address], {
            "partner_id": owner.partner_id.id,
            "public_name": owner.partner_id.public_name,
        })

    def test_active_wallet_name(self):
        self._make_wallet(self.owner)
        self._assert_owner(self._contact([self.address]), self.owner)

    def test_archived_wallet_name_without_restoring_wallet(self):
        wallet = self._make_wallet(self.owner)
        wallet.active = False

        result = self._contact([self.address, "unknown-address"])

        self.assertEqual(set(result), {self.address})
        self._assert_owner(result, self.owner)
        self.assertFalse(wallet.active)
        self.assertNotIn(wallet, self.owner.partner_id.lcc_backend_ids)
        self.assertNotIn(
            wallet, self.owner.partner_id.get_wallets_by_currency_type(self.wallet_type)
        )

    def test_active_owner_wins_over_archived_owner(self):
        active_wallet = self._make_wallet(self.owner)
        self._make_wallet(self.other_owner, active=False)
        self._assert_owner(self._contact([self.address]), self.owner)

        # Also cover an active registration newer than the archived records.
        active_wallet.active = False
        self._make_wallet(self.other_owner)
        self._assert_owner(self._contact([self.address]), self.other_owner)

    def test_latest_archived_owner_is_used_when_all_are_archived(self):
        self._make_wallet(self.owner, active=False)
        self._make_wallet(self.other_owner, active=False)
        self._assert_owner(self._contact([self.address]), self.other_owner)

    def test_unknown_address(self):
        self._make_wallet(self.owner, active=False)
        self.assertEqual(self._contact(["unknown-address"]), {})

    def test_empty_addresses(self):
        self._make_wallet(self.owner, active=False)
        self.assertEqual(self._contact([]), {})

    def test_archived_partner_is_not_exposed(self):
        self._make_wallet(self.other_owner, active=False)
        self.other_owner.active = False
        self.other_owner.partner_id.active = False
        self.assertEqual(self._contact([self.address]), {})
