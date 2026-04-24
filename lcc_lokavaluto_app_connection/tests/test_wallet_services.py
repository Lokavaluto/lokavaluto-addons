from unittest.mock import patch

from minimock import Mock

from odoo.exceptions import AccessDenied
from odoo.tests.common import TransactionCase

import odoo.addons.lcc_lokavaluto_app_connection.services as svc
from odoo.addons.lcc_lokavaluto_app_connection.services import lcc_api


class TestWalletServiceBase(TransactionCase):
    """Test base WalletService."""

    def _get_wallet_service(self):
        collection = self.env["lokavaluto.private.services"].browse(1)
        with collection.work_on("res.partner.backend") as work:
            return work.component(usage="wallet")

    def _call_with_mock_request(self, endpoint, headers=None):
        mock_request = Mock(
            "request",
            httprequest=Mock("httprequest", headers=headers or {}),
        )
        with patch.object(svc, "request", mock_request):
            return endpoint()

    def test_auth_user_uri_returns_empty_actions(self):
        """Base _auth_user_uri returns empty list (no-op)."""
        service = self._get_wallet_service()
        result = service._auth_user_uri("foo://test/user/alice")
        self.assertEqual(result, [])

    def test_lcc_api_with_base_auth_passes_without_gate(self):
        """@lcc_api with require_actions=None passes with base no-op auth."""
        service = self._get_wallet_service()
        result = {}

        @lcc_api([(["/test"], "GET")])
        def dummy(self):
            result["called"] = True
            return True

        self._call_with_mock_request(
            lambda: dummy(service),
            headers={"X-Lokapi-Caller-User-Uri": "foo://test/user/alice"},
        )
        self.assertTrue(result["called"])

    def test_lcc_api_with_base_auth_rejects_with_gate(self):
        """@lcc_api with an admin gate rejects when base returns []."""
        from odoo.addons.lcc_lokavaluto_app_connection.services.gate import (
            ANY_ADMIN_ACTION,
        )

        service = self._get_wallet_service()

        @lcc_api([(["/test"], "GET")], require_actions=ANY_ADMIN_ACTION)
        def dummy(self):
            return True

        with self.assertRaises(AccessDenied):
            self._call_with_mock_request(
                lambda: dummy(service),
                headers={"X-Lokapi-Caller-User-Uri": "foo://test/user/alice"},
            )


class TestWalletServiceContactInfo(TransactionCase):
    """Test base ``_contact_info`` helper behaviour.

    Exercises the unguarded base implementation: the shape of the
    returned dict, the issuer being taken from the caller's company,
    and the optional ``logo`` field.  Comchain permission gating is
    covered in ``lcc_comchain_base`` tests.
    """

    def _get_wallet_service(self):
        collection = self.env["lokavaluto.private.services"].browse(1)
        with collection.work_on("res.partner.backend") as work:
            return work.component(usage="wallet")

    def _make_partner(self, **kw):
        vals = {
            "name": "John Doe",
            "street": "1 rue du Test",
            "street2": "Bat. B",
            "city": "Testville",
            "zip": "75000",
            "email": "john@example.com",
            "phone": "+33 1 23 45 67 89",
            "mobile": "+33 6 12 34 56 78",
            "website": "https://example.com",
        }
        vals.update(kw)
        return self.env["res.partner"].create(vals)

    def _make_wallet(self, partner):
        currency_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        currency = self.env["res.alt.currency"].create(
            {
                "name": "Test Base Currency",
                "ident": "testbase",
                "active": True,
                "engine": "foo",
                "currency_unit_product_id": currency_product.id,
            }
        )
        return self.env["res.partner.backend"].create(
            {
                "partner_id": partner.id,
                "name": "testbase:stub",
                "ident": "stub",
                "alt_currency_id": currency.id,
            }
        )

    def test_contact_info_returns_issuer_and_user_keys(self):
        """``_contact_info`` returns a dict with ``issuer`` and ``user``."""
        partner = self._make_partner()
        wallet = self._make_wallet(partner)
        service = self._get_wallet_service()
        result = service._contact_info(wallet)
        self.assertIn("issuer", result)
        self.assertIn("user", result)

    def test_contact_info_user_fields_match_partner(self):
        """``user`` sub-dict exposes the wallet partner's contact fields."""
        partner = self._make_partner(
            name="Jane",
            street="5 rue du Code",
            street2="Apt 2",
            city="Pyville",
            zip="69000",
            email="jane@example.com",
            phone="0102030405",
            mobile="0607080910",
            website="https://jane.example",
        )
        wallet = self._make_wallet(partner)
        service = self._get_wallet_service()
        result = service._contact_info(wallet)
        user = result["user"]
        self.assertEqual(user["name"], "Jane")
        self.assertEqual(user["street"], "5 rue du Code")
        self.assertEqual(user["street2"], "Apt 2")
        self.assertEqual(user["city"], "Pyville")
        self.assertEqual(user["zip"], "69000")
        self.assertEqual(user["email"], "jane@example.com")
        self.assertEqual(user["phone"], "0102030405")
        self.assertEqual(user["mobile"], "0607080910")
        self.assertEqual(user["website"], "https://jane.example")

    def test_contact_info_issuer_is_caller_company(self):
        """``issuer`` fields come from ``env.user.company_id``."""
        company = self.env["res.company"].create({"name": "Issuer Corp"})
        ## Run the service under a user attached to *company*
        user = self.env["res.users"].create(
            {
                "name": "Caller",
                "login": "caller_ci",
                "company_id": company.id,
                "company_ids": [(6, 0, [company.id])],
            }
        )
        partner = self._make_partner()
        wallet = self._make_wallet(partner)
        collection = self.env["lokavaluto.private.services"].with_user(user).browse(1)
        with collection.work_on("res.partner.backend") as work:
            service = work.component(usage="wallet")
            result = service._contact_info(wallet)
        self.assertEqual(result["issuer"]["name"], "Issuer Corp")

    def test_contact_info_issuer_includes_logo(self):
        """``issuer`` dict exposes ``logo`` (``res.company`` has the field)."""
        partner = self._make_partner()
        wallet = self._make_wallet(partner)
        service = self._get_wallet_service()
        result = service._contact_info(wallet)
        ## ``res.company`` has a ``logo`` field in Odoo 16, so the
        ## ``hasattr(p, "logo")`` branch always yields ``logo`` on the
        ## issuer side.
        self.assertIn("logo", result["issuer"])
