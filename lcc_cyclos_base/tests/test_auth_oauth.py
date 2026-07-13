from odoo.addons.component.tests.common import TransactionComponentCase
from odoo.exceptions import AccessDenied


class TestCyclosAuthOauth(TransactionComponentCase):
    """Cyclos OAuth login: e-mail reconciliation + ``res.partner.backend``
    creation, with fail-loud preconditions (RAF of lok/2631)."""

    def setUp(self):
        super().setUp()

        self.ResUsers = self.env["res.users"]
        self.ResPartner = self.env["res.partner"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.ResAltCurrency = self.env["res.alt.currency"]
        self.AuthProvider = self.env["auth.oauth.provider"]

        self.currency_unit_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()

        # A Cyclos currency on a known server domain.
        self.cyclos_currency = self.ResAltCurrency.create(
            {
                "name": "Cyclos Test Currency",
                "ident": "cyclostest",
                "active": True,
                "engine": "cyclos",
                "currency_unit_product_id": self.currency_unit_product.id,
                "cyclos_server_url": "https://cyclos.example.test/api",
            }
        )

        # The matching OAuth provider (Cyclos OIDC endpoints).
        self.provider = self.AuthProvider.create(
            {
                "name": "cyclos",
                "client_id": "odoo",
                "scope": "openid profile email",
                "auth_endpoint": "https://cyclos.example.test/api/oidc/authorize",
                "validation_endpoint": "https://cyclos.example.test/api/oidc/token",
                "data_endpoint": "https://cyclos.example.test/api/oidc/userinfo",
                "body": "Se connecter avec Cyclos",
                "enabled": True,
            }
        )

        # A non-Cyclos provider (no /api/oidc/ in its endpoints).
        self.other_provider = self.AuthProvider.create(
            {
                "name": "other",
                "client_id": "other",
                "scope": "openid",
                "auth_endpoint": "https://accounts.example.org/o/oauth2/auth",
                "validation_endpoint": "https://accounts.example.org/token",
                "body": "Other",
                "enabled": True,
            }
        )

        self.cyclos_uid = "test-cyclos-uid-0001"
        self.oauth_data = {
            "user_id": self.cyclos_uid,
            "name": "Alice Cyclos",
            "email": "alice@example.test",
            "preferred_username": "alice",
        }
        self.params = {"access_token": "tok-abc", "state": "{}"}

    # --- provider detection -------------------------------------------------

    def test_is_cyclos_by_oidc_path(self):
        # Detected by the /api/oidc/ endpoint convention, not by currency
        # presence.
        self.assertTrue(self.provider._is_cyclos())
        self.assertFalse(self.other_provider._is_cyclos())

    def test_is_cyclos_stable_under_host_drift(self):
        # Even if endpoints point to a different host (IP drift), as long
        # as the /api/oidc/ path is present it is still detected as Cyclos.
        drifted = self.AuthProvider.create(
            {
                "name": "cyclos-drift",
                "client_id": "odoo",
                "scope": "openid profile email",
                "auth_endpoint": "http://10.0.0.99:8080/api/oidc/authorize",
                "validation_endpoint": "http://10.0.0.99:8080/api/oidc/token",
                "data_endpoint": "http://10.0.0.99:8080/api/oidc/userinfo",
                "body": "x",
                "enabled": True,
            }
        )
        self.assertTrue(drifted._is_cyclos())

    def test_signin_requires_preferred_username(self):
        # Cyclos endpoints but userinfo lacks preferred_username -> the
        # login is NOT treated as Cyclos: it defers to the base signin
        # (which must not raise our Cyclos-specific AccessDenied).
        oauth_data = {"user_id": "x", "email": "x@example.test"}
        try:
            self.ResUsers._auth_oauth_signin(
                self.provider.id, oauth_data, dict(self.params)
            )
        except AccessDenied as e:
            self.assertNotIn("Cyclos", str(e))
        except Exception:
            pass

    def test_alt_currency_for_provider(self):
        currency = self.provider._cyclos_alt_currency()
        self.assertEqual(currency, self.cyclos_currency)

    def test_alt_currency_empty_on_domain_mismatch(self):
        # Provider on a host that no currency advertises -> empty recordset.
        drifted = self.AuthProvider.create(
            {
                "name": "cyclos-drift",
                "client_id": "odoo",
                "scope": "openid profile email",
                "auth_endpoint": "http://10.0.0.99:8080/api/oidc/authorize",
                "validation_endpoint": "http://10.0.0.99:8080/api/oidc/token",
                "data_endpoint": "http://10.0.0.99:8080/api/oidc/userinfo",
                "body": "x",
                "enabled": True,
            }
        )
        currency = drifted._cyclos_alt_currency()
        self.assertFalse(currency)

    # --- signin: non-Cyclos provider untouched ------------------------------

    def test_non_cyclos_provider_defers_to_base(self):
        # A non-Cyclos provider must not trigger any Cyclos logic; here we
        # simply assert it does not raise our Cyclos-specific AccessDenied
        # about missing currency (it goes through the base path, which will
        # fail later for unrelated reasons -- not our concern).
        oauth_data = {"user_id": "x", "email": "x@example.org"}
        try:
            self.ResUsers._auth_oauth_signin(
                self.other_provider.id, oauth_data, dict(self.params)
            )
        except AccessDenied as e:
            self.assertNotIn("Cyclos", str(e))
        except Exception:
            pass

    # --- signin: fail-loud preconditions ------------------------------------

    def test_cyclos_provider_without_currency_raises(self):
        drifted = self.AuthProvider.create(
            {
                "name": "cyclos-drift",
                "client_id": "odoo",
                "scope": "openid profile email",
                "auth_endpoint": "http://10.0.0.99:8080/api/oidc/authorize",
                "validation_endpoint": "http://10.0.0.99:8080/api/oidc/token",
                "data_endpoint": "http://10.0.0.99:8080/api/oidc/userinfo",
                "body": "x",
                "enabled": True,
            }
        )
        with self.assertRaises(AccessDenied):
            self.ResUsers._auth_oauth_signin(
                drifted.id, dict(self.oauth_data), dict(self.params)
            )

    def test_cyclos_login_without_email_raises(self):
        oauth_data = {
            "user_id": self.cyclos_uid,
            "name": "No Email",
            "preferred_username": "noemail",
        }
        with self.assertRaises(AccessDenied):
            self.ResUsers._auth_oauth_signin(
                self.provider.id, oauth_data, dict(self.params)
            )

    def test_cyclos_login_with_empty_email_raises(self):
        oauth_data = dict(self.oauth_data)
        oauth_data["email"] = ""
        with self.assertRaises(AccessDenied):
            self.ResUsers._auth_oauth_signin(
                self.provider.id, oauth_data, dict(self.params)
            )

    # --- reconciliation by e-mail ------------------------------------------

    def test_reconcile_links_existing_user_by_email(self):
        existing = self.ResUsers.create(
            {
                "name": "Alice Existing",
                "login": "alice@example.test",
                "email": "alice@example.test",
            }
        )
        self.assertFalse(existing.oauth_uid)

        login = self.ResUsers._auth_oauth_signin(
            self.provider.id, dict(self.oauth_data), dict(self.params)
        )

        self.assertEqual(login, existing.login)
        existing.invalidate_recordset()
        self.assertEqual(existing.oauth_uid, self.cyclos_uid)
        self.assertEqual(existing.oauth_provider_id, self.provider)
        self.assertEqual(
            self.ResUsers.search_count([("login", "=", "alice@example.test")]),
            1,
        )
        # backend created for the reconciled user.
        backend = self.ResPartnerBackend.search(
            [
                ("partner_id", "=", existing.partner_id.id),
                ("type", "=", "cyclos"),
                ("alt_currency_id", "=", self.cyclos_currency.id),
                ("cyclos_id", "=", self.cyclos_uid),
            ]
        )
        self.assertEqual(len(backend), 1)

    def test_already_linked_user_is_reused(self):
        linked = self.ResUsers.create(
            {
                "name": "Bob Linked",
                "login": "bob@example.test",
                "email": "bob@example.test",
                "oauth_provider_id": self.provider.id,
                "oauth_uid": self.cyclos_uid,
            }
        )
        oauth_data = dict(self.oauth_data)
        oauth_data["email"] = "bob@example.test"

        login = self.ResUsers._auth_oauth_signin(
            self.provider.id, oauth_data, dict(self.params)
        )
        self.assertEqual(login, linked.login)
        self.assertEqual(
            self.ResUsers.search_count([("oauth_uid", "=", self.cyclos_uid)]),
            1,
        )
        # access token refreshed on the reused user.
        linked.invalidate_recordset()
        self.assertEqual(linked.oauth_access_token, "tok-abc")

    # --- reconciliation with a pre-existing partner -------------------------

    def test_user_created_on_preexisting_partner(self):
        # A partner exists with the Cyclos e-mail but has NO user (e.g. a
        # member without a login): the new user must be attached to that
        # partner, not duplicate it.
        partner = self.ResPartner.create(
            {"name": "Norbert NoUser", "email": "alice@example.test"}
        )
        partners_before = self.ResPartner.search_count([])

        login = self.ResUsers._auth_oauth_signin(
            self.provider.id, dict(self.oauth_data), dict(self.params)
        )

        user = self.ResUsers.search([("login", "=", login)])
        self.assertEqual(len(user), 1)
        # attached to the pre-existing partner, no new partner created.
        self.assertEqual(user.partner_id, partner)
        self.assertEqual(self.ResPartner.search_count([]), partners_before)
        # oauth identity linked + wallet backend on that same partner.
        self.assertEqual(user.oauth_uid, self.cyclos_uid)
        backend = self.ResPartnerBackend.search(
            [
                ("partner_id", "=", partner.id),
                ("type", "=", "cyclos"),
                ("cyclos_id", "=", self.cyclos_uid),
            ]
        )
        self.assertEqual(len(backend), 1)

    def test_partner_for_email_partner_with_user_raises(self):
        # A main profile partner that already has a user is an
        # inconsistency at this point: the user should have been found by
        # the e-mail reconciliation step (its login/e-mail diverged from
        # the partner's e-mail) -> explicit error, no silent skip.
        user = self.ResUsers.create(
            {
                "name": "Paula",
                "login": "paula-login@example.test",
                "email": "paula-login@example.test",
            }
        )
        # partner e-mail diverged from the user's login/e-mail
        user.partner_id.email = "paula@example.test"
        with self.assertRaises(AccessDenied):
            self.ResUsers._cyclos_partner_for_email("paula@example.test")

    def test_partner_for_email_ignores_non_main_profiles(self):
        # Public/position profiles are projections of a main profile and
        # must not be candidates.
        main = self.ResPartner.create(
            {"name": "Quentin", "email": "quentin-main@example.test"}
        )
        self.ResPartner.create(
            {
                "name": "Quentin public",
                "email": "quentin@example.test",
                "type": "other",
                "contact_id": main.id,
                "partner_profile": self.env.ref(
                    "partner_profiles.partner_profile_public"
                ).id,
            }
        )
        self.assertFalse(
            self.ResUsers._cyclos_partner_for_email("quentin@example.test")
        )

    def test_partner_for_email_ambiguous_raises(self):
        # Two partners may share an e-mail across kinds (lcc_members only
        # forbids duplicates among main profiles of the same kind).
        self.ResPartner.create(
            {"name": "Twin person", "email": "twin@example.test"}
        )
        self.ResPartner.create(
            {
                "name": "Twin company",
                "email": "twin@example.test",
                "is_company": True,
            }
        )
        with self.assertRaises(AccessDenied):
            self.ResUsers._cyclos_partner_for_email("twin@example.test")

    # --- backend creation ---------------------------------------------------

    def test_ensure_backend_creates_when_absent(self):
        user = self.ResUsers.create(
            {
                "name": "Carol",
                "login": "carol@example.test",
                "email": "carol@example.test",
            }
        )
        backend = user._cyclos_ensure_wallet(
            self.cyclos_currency, self.cyclos_uid
        )
        self.assertEqual(backend.type, "cyclos")
        self.assertEqual(backend.cyclos_id, self.cyclos_uid)
        self.assertEqual(backend.alt_currency_id, self.cyclos_currency)
        self.assertEqual(backend.name, f"cyclos:{self.cyclos_uid}")

    def test_ensure_backend_idempotent(self):
        user = self.ResUsers.create(
            {
                "name": "Dan",
                "login": "dan@example.test",
                "email": "dan@example.test",
            }
        )
        b1 = user._cyclos_ensure_wallet(
            self.cyclos_currency, self.cyclos_uid
        )
        b2 = user._cyclos_ensure_wallet(
            self.cyclos_currency, self.cyclos_uid
        )
        self.assertEqual(b1, b2)
        self.assertEqual(
            self.ResPartnerBackend.search_count(
                [
                    ("partner_id", "=", user.partner_id.id),
                    ("type", "=", "cyclos"),
                    ("cyclos_id", "=", self.cyclos_uid),
                ]
            ),
            1,
        )

    def test_ensure_backend_coexists_with_other_wallets(self):
        # A partner may already own OTHER cyclos wallets (different cyclos_id);
        # that is NOT a conflict -- the new one is created alongside.
        user = self.ResUsers.create(
            {
                "name": "Gina",
                "login": "gina@example.test",
                "email": "gina@example.test",
            }
        )
        self.ResPartnerBackend.create(
            {
                "partner_id": user.partner_id.id,
                "alt_currency_id": self.cyclos_currency.id,
                "cyclos_id": "another-wallet-id",
                "name": "cyclos:another-wallet-id",
                "cyclos_status": "active",
            }
        )
        backend = user._cyclos_ensure_wallet(
            self.cyclos_currency, self.cyclos_uid
        )
        self.assertEqual(backend.cyclos_id, self.cyclos_uid)
        # both wallets coexist on the partner.
        self.assertEqual(
            self.ResPartnerBackend.search_count(
                [
                    ("partner_id", "=", user.partner_id.id),
                    ("type", "=", "cyclos"),
                ]
            ),
            2,
        )

    def test_ensure_backend_same_cyclos_id_other_partner_raises(self):
        # Same cyclos_id already attached to a DIFFERENT partner -> integrity
        # error -> raise.
        other_partner = self.ResPartner.create({"name": "Other Owner"})
        self.ResPartnerBackend.create(
            {
                "partner_id": other_partner.id,
                "alt_currency_id": self.cyclos_currency.id,
                "cyclos_id": self.cyclos_uid,
                "name": f"cyclos:{self.cyclos_uid}",
                "cyclos_status": "active",
            }
        )
        user = self.ResUsers.create(
            {
                "name": "Helen",
                "login": "helen@example.test",
                "email": "helen@example.test",
            }
        )
        with self.assertRaises(AccessDenied):
            user._cyclos_ensure_wallet(
                self.cyclos_currency, self.cyclos_uid
            )

    def test_ensure_backend_no_currency_raises(self):
        user = self.ResUsers.create(
            {
                "name": "Ian",
                "login": "ian@example.test",
                "email": "ian@example.test",
            }
        )
        with self.assertRaises(AccessDenied):
            user._cyclos_ensure_wallet(
                self.env["res.alt.currency"], self.cyclos_uid
            )
