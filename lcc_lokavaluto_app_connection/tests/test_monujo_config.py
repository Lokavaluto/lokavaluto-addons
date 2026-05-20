"""Tests for ``lcc.monujo.config`` and the ``/config`` REST endpoint.

Covers:
- Default seed integrity (the install creates a default record).
- ``to_monujo_dict`` wire shape (keys + values vs config.sample.json).
- The single-default and unique-ident constraints.
- The local_auth_policy JSON validation.
- REST behaviour: GET /config without ident, with ident, and with a
  bogus ident.

The REST tests invoke the service component directly through
``base_rest``'s ``WorkContext`` rather than going through HTTP. This
sidesteps the well-known limitation that ``HttpCase`` in Odoo 16 does
not load ``base_rest``-generated controllers into the test routing
map. Calling the component directly exercises the same code path the
HTTP dispatcher would use after URL resolution — i.e. the actual
business logic — and is the pattern recommended by OCA base_rest.
"""

import json

from psycopg2 import IntegrityError

from odoo.exceptions import MissingError, ValidationError
from odoo.tools import mute_logger

from odoo.addons.component.tests.common import TransactionComponentCase


# Keys the /mobile-config wire format MUST include.
EXPECTED_MOBILE_TOP_LEVEL_KEYS = {
    "ident",
    "appName",
    "iconUrl",
    "splashUrl",
    "androidPlayStoreAppId",
    "iosAppStoreAppId",
}


# Keys the Monujo wire format MUST include. Mirrors the top-level
# shape of monujo/public/config.sample.json plus our new *Url fields.
EXPECTED_TOP_LEVEL_KEYS = {
    "appName",
    "lokapiDb",
    "lokapiHost",
    "mapUrl",
    "helpUrl",
    "cguUrl",
    "logoUrl",
    "loginLogoUrl",
    "faviconUrl",
    "locales",
    "theme",
    "css",
    "accountsRefreshInterval",
    "transactionsRefreshInterval",
    "currenciesRefreshInterval",
    "disableReconversion",
    "disableTopUp",
    "disableSplitMemo",
    "disableBadges",
    "disableImportWallet",
    "disableDisplayOtherUnpaidTopup",
    "localAuthPolicy",
}


class TestMonujoConfigModel(TransactionComponentCase):
    """Pure-model tests — no HTTP layer involved."""

    def setUp(self):
        super().setUp()
        self.Config = self.env["lcc.monujo.config"]
        self.Theme = self.env["lcc.monujo.config.theme.entry"]
        self.Language = self.env["lcc.monujo.config.language"]
        self.default = self.env.ref(
            "lcc_lokavaluto_app_connection.lcc_monujo_config_default"
        )

    # -- Seed integrity ------------------------------------------------

    def test_default_record_seeded(self):
        """A default record is created at install."""
        self.assertTrue(self.default)
        self.assertTrue(self.default.is_default)
        self.assertEqual(self.default.ident, "default")

    def test_default_record_has_english_language(self):
        """The default record ships with an English language entry."""
        en_entry = self.default.language_ids.filtered(
            lambda lang: lang.code == "en_US"
        )
        # res.lang code for English (US) on Odoo 16 is 'en_US'.
        self.assertEqual(len(en_entry), 1)
        # The English entry has no translation_file (bundled in app).
        self.assertFalse(en_entry.translation_file)

    def test_default_record_has_theme_entries(self):
        """The default record ships with the full theme palette."""
        # config.sample.json defines ~45 theme entries.
        self.assertGreaterEqual(len(self.default.theme_entry_ids), 40)
        keys = {e.key for e in self.default.theme_entry_ids}
        # Spot-check a few known keys.
        self.assertIn("color-1", keys)
        self.assertIn("color-2", keys)
        self.assertIn("primary-color", keys)

    # -- Wire shape ----------------------------------------------------

    def test_to_monujo_dict_top_level_keys(self):
        """``to_monujo_dict`` returns exactly the expected top-level keys."""
        payload = self.default.to_monujo_dict(base_url="https://odoo.example.org")
        self.assertEqual(set(payload.keys()), EXPECTED_TOP_LEVEL_KEYS)

    def test_to_monujo_dict_locales_shape(self):
        """``locales`` block has the expected sub-structure."""
        payload = self.default.to_monujo_dict()
        self.assertEqual(
            set(payload["locales"].keys()),
            {
                "appStringsLanguage",
                "defaultLanguage",
                "preferNavigatorLanguage",
                "availableLanguages",
            },
        )

    def test_to_monujo_dict_theme_is_flat_dict(self):
        """``theme`` is serialized as ``{key: value}``."""
        payload = self.default.to_monujo_dict()
        self.assertIsInstance(payload["theme"], dict)
        self.assertEqual(payload["theme"]["color-1"], "#e4f2f1")
        self.assertEqual(payload["theme"]["color-2"], "#009688")

    def test_to_monujo_dict_image_urls_none_when_unset(self):
        """Image URLs are ``None`` when no image is uploaded."""
        payload = self.default.to_monujo_dict(base_url="https://odoo.example.org")
        # Default seed has no images.
        self.assertIsNone(payload["faviconUrl"])
        self.assertIsNone(payload["logoUrl"])
        self.assertIsNone(payload["loginLogoUrl"])

    def test_to_monujo_dict_image_url_when_set(self):
        """Image URL points to ``/web/image/<model>/<id>/<field>``.

        Uses a fresh record rather than mutating the shared seed:
        ``fields.Image(attachment=True)`` writes through
        ``ir.attachment`` rows, which the surrounding
        ``TransactionCase`` rollback does not always undo cleanly
        for module-data records flagged ``noupdate="1"``.
        """
        # Use a tiny 1x1 PNG (base64).
        tiny_png = (
            b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42m"
            b"NkAAIAAAoAAv/lxKUAAAAASUVORK5CYII="
        )
        cfg = self.Config.create(
            {
                "name": "Image URL test",
                "ident": "image-url-test",
                "favicon": tiny_png,
            }
        )
        payload = cfg.to_monujo_dict(base_url="https://odoo.example.org")
        self.assertEqual(
            payload["faviconUrl"],
            "https://odoo.example.org/web/image/lcc.monujo.config/%d/favicon"
            % cfg.id,
        )

    def test_to_monujo_dict_local_auth_policy_decoded(self):
        """``localAuthPolicy`` is decoded from JSON, not emitted as a string."""
        payload = self.default.to_monujo_dict()
        # The seed sets ["Retention", {"time": 900, ...}]
        self.assertIsInstance(payload["localAuthPolicy"], list)
        self.assertEqual(payload["localAuthPolicy"][0], "Retention")
        self.assertEqual(payload["localAuthPolicy"][1]["time"], 900)

    def test_to_monujo_dict_local_auth_policy_none_when_unset(self):
        """``localAuthPolicy`` is ``None`` when no policy is configured."""
        cfg = self.Config.create(
            {"name": "Bare", "ident": "bare", "local_auth_policy": False}
        )
        payload = cfg.to_monujo_dict()
        self.assertIsNone(payload["localAuthPolicy"])

    # -- Constraints ---------------------------------------------------

    def test_unique_ident(self):
        """Two configs cannot share an ident."""
        self.Config.create({"name": "First", "ident": "shared"})
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.Config.create({"name": "Second", "ident": "shared"})

    def test_single_default(self):
        """At most one config can be marked default."""
        with self.assertRaises(ValidationError):
            self.Config.create(
                {"name": "Second default", "ident": "second", "is_default": True}
            )

    def test_invalid_local_auth_policy_rejected(self):
        """Non-JSON local_auth_policy is rejected on write."""
        cfg = self.Config.create({"name": "JSON test", "ident": "json-test"})
        with self.assertRaises(ValidationError):
            cfg.write({"local_auth_policy": "this is not json"})

    def test_valid_local_auth_policy_accepted(self):
        """Valid JSON local_auth_policy is accepted."""
        cfg = self.Config.create({"name": "JSON test 2", "ident": "json-test-2"})
        cfg.write({"local_auth_policy": '["X", {"y": 1}]'})
        self.assertEqual(json.loads(cfg.local_auth_policy), ["X", {"y": 1}])

    def test_unique_language_per_config(self):
        """A language may appear at most once per config."""
        cfg = self.Config.create({"name": "Lang test", "ident": "lang-test"})
        en = self.env.ref("base.lang_en")
        self.Language.create({"config_id": cfg.id, "lang_id": en.id})
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.Language.create({"config_id": cfg.id, "lang_id": en.id})

    def test_unique_theme_key_per_config(self):
        """A theme key may appear at most once per config."""
        cfg = self.Config.create({"name": "Theme test", "ident": "theme-test"})
        self.Theme.create(
            {"config_id": cfg.id, "key": "color-1", "value": "#ffffff"}
        )
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.Theme.create(
                    {"config_id": cfg.id, "key": "color-1", "value": "#000000"}
                )

    def test_cascade_delete(self):
        """Deleting a config cascades to its theme/language children."""
        cfg = self.Config.create({"name": "Cascade", "ident": "cascade"})
        self.Theme.create(
            {"config_id": cfg.id, "key": "k", "value": "v"}
        )
        self.Language.create(
            {"config_id": cfg.id, "lang_id": self.env.ref("base.lang_en").id}
        )
        theme_count_before = self.Theme.search_count(
            [("config_id", "=", cfg.id)]
        )
        lang_count_before = self.Language.search_count(
            [("config_id", "=", cfg.id)]
        )
        self.assertEqual(theme_count_before, 1)
        self.assertEqual(lang_count_before, 1)
        cfg.unlink()
        self.assertEqual(
            self.Theme.search_count([("config_id", "=", cfg.id)]), 0
        )
        self.assertEqual(
            self.Language.search_count([("config_id", "=", cfg.id)]), 0
        )


class TestMonujoConfigEndpoint(TransactionComponentCase):
    """Service-component tests for the ``config`` REST endpoint.

    Invokes ``ConfigService.get`` directly via base_rest's
    ``WorkContext`` rather than going through HTTP. See module
    docstring for rationale.
    """

    def setUp(self):
        super().setUp()
        self.default = self.env.ref(
            "lcc_lokavaluto_app_connection.lcc_monujo_config_default"
        )

    def _call(self, **params):
        """Resolve ``config.service`` from the public collection and
        invoke its ``get`` method with the given query-string params.

        Mirrors the pattern used by other service tests in this
        module (e.g. ``test_partner_services_search.py``): grab a
        bound recordset for the collection model, then ``work_on``
        any concrete model — the model name is irrelevant for our
        service since it only reads from ``self.env``.
        """
        collection = self.env["lokavaluto.public.services"].browse(1)
        with collection.work_on("lcc.monujo.config") as work:
            service = work.component(usage="config")
            return service.get(**params)

    def test_get_without_ident_returns_default(self):
        """``get()`` (no ident) returns the default record's payload."""
        payload = self._call()
        self.assertEqual(payload["appName"], self.default.name)

    def test_get_with_ident_returns_matching_record(self):
        """``get(ident="default")`` returns the default record."""
        payload = self._call(ident="default")
        self.assertEqual(payload["appName"], self.default.name)

    def test_get_with_unknown_ident_raises(self):
        """``get(ident="nonexistent")`` raises ``MissingError``."""
        with self.assertRaises(MissingError):
            self._call(ident="does-not-exist")

    def test_get_payload_has_all_expected_keys(self):
        """Wire payload matches the documented top-level key set."""
        payload = self._call()
        self.assertEqual(set(payload.keys()), EXPECTED_TOP_LEVEL_KEYS)

    def test_get_payload_includes_theme_keys(self):
        """Theme is serialized as a flat ``{key: value}`` dict."""
        payload = self._call()
        self.assertIsInstance(payload["theme"], dict)
        self.assertEqual(payload["theme"]["color-1"], "#e4f2f1")

    def test_get_payload_locales_shape(self):
        """``locales`` block carries the four expected sub-keys."""
        payload = self._call()
        self.assertEqual(
            set(payload["locales"].keys()),
            {
                "appStringsLanguage",
                "defaultLanguage",
                "preferNavigatorLanguage",
                "availableLanguages",
            },
        )


class TestMonujoMobileConfigSerializer(TransactionComponentCase):
    """Pure-model tests for ``to_mobile_dict``.

    Tests that mutate mobile fields create fresh records rather than
    writing to the seeded default — see
    :meth:`TestMonujoConfigModel.test_to_monujo_dict_image_url_when_set`
    for the rationale.
    """

    def setUp(self):
        super().setUp()
        self.Config = self.env["lcc.monujo.config"]
        self.default = self.env.ref(
            "lcc_lokavaluto_app_connection.lcc_monujo_config_default"
        )

    def test_to_mobile_dict_top_level_keys(self):
        """``to_mobile_dict`` returns exactly the expected top-level keys."""
        payload = self.default.to_mobile_dict(
            base_url="https://odoo.example.org"
        )
        self.assertEqual(set(payload.keys()), EXPECTED_MOBILE_TOP_LEVEL_KEYS)

    def test_to_mobile_dict_ident_echoed(self):
        """``ident`` field is echoed in the response."""
        payload = self.default.to_mobile_dict()
        self.assertEqual(payload["ident"], self.default.ident)

    def test_to_mobile_dict_image_urls_none_when_unset(self):
        """Icon / splash URLs are ``None`` when no image is uploaded."""
        payload = self.default.to_mobile_dict(
            base_url="https://odoo.example.org"
        )
        self.assertIsNone(payload["iconUrl"])
        self.assertIsNone(payload["splashUrl"])

    def test_to_mobile_dict_image_url_when_set(self):
        """Icon URL points to ``/web/image/<model>/<id>/mobile_icon``."""
        tiny_png = (
            b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42m"
            b"NkAAIAAAoAAv/lxKUAAAAASUVORK5CYII="
        )
        cfg = self.Config.create(
            {
                "name": "Mobile image test",
                "ident": "mobile-image-test",
                "mobile_icon": tiny_png,
            }
        )
        payload = cfg.to_mobile_dict(base_url="https://odoo.example.org")
        self.assertEqual(
            payload["iconUrl"],
            "https://odoo.example.org/web/image/lcc.monujo.config/%d/mobile_icon"
            % cfg.id,
        )

    def test_to_mobile_dict_store_ids_none_when_unset(self):
        """Store IDs are ``None`` when not configured."""
        payload = self.default.to_mobile_dict()
        self.assertIsNone(payload["androidPlayStoreAppId"])
        self.assertIsNone(payload["iosAppStoreAppId"])

    def test_to_mobile_dict_app_name_none_when_unset(self):
        """``appName`` is ``None`` when ``mobile_app_name`` is unset."""
        payload = self.default.to_mobile_dict()
        self.assertIsNone(payload["appName"])

    def test_to_mobile_dict_app_name_emitted(self):
        """``mobile_app_name`` flows through to wire as ``appName``."""
        cfg = self.Config.create(
            {
                "name": "App name test",
                "ident": "app-name-test",
                "mobile_app_name": "Monujo",
            }
        )
        payload = cfg.to_mobile_dict()
        self.assertEqual(payload["appName"], "Monujo")

    def test_to_mobile_dict_app_name_independent_from_label(self):
        """``mobile_app_name`` is independent from the record's ``name``.

        The two are intentionally decoupled: the record label
        is admin-facing, the mobile app name appears under the
        launcher icon. Setting one MUST NOT affect the other.
        """
        cfg = self.Config.create(
            {
                "name": "Long Label For Admins",
                "ident": "indep-test",
                "mobile_app_name": "Monujo",
            }
        )
        # Mobile payload emits the mobile name, NOT the label.
        mobile_payload = cfg.to_mobile_dict()
        self.assertEqual(mobile_payload["appName"], "Monujo")
        # Config payload still emits the label.
        config_payload = cfg.to_monujo_dict()
        self.assertEqual(config_payload["appName"], "Long Label For Admins")

    def test_to_mobile_dict_store_ids_emitted(self):
        """Store IDs flow through to the wire payload."""
        cfg = self.Config.create(
            {
                "name": "Store IDs test",
                "ident": "store-ids-test",
                "android_play_store_app_id": "fr.lokavaluto.monujo",
                "ios_app_store_app_id": "1234567890",
            }
        )
        payload = cfg.to_mobile_dict()
        self.assertEqual(
            payload["androidPlayStoreAppId"], "fr.lokavaluto.monujo"
        )
        self.assertEqual(payload["iosAppStoreAppId"], "1234567890")


class TestMonujoMobileConfigEndpoint(TransactionComponentCase):
    """Service-component tests for the ``mobile-config`` REST endpoint."""

    def setUp(self):
        super().setUp()
        self.default = self.env.ref(
            "lcc_lokavaluto_app_connection.lcc_monujo_config_default"
        )

    def _call(self, **params):
        collection = self.env["lokavaluto.public.services"].browse(1)
        with collection.work_on("lcc.monujo.config") as work:
            service = work.component(usage="mobile-config")
            return service.get(**params)

    def test_get_without_ident_returns_default(self):
        """``get()`` (no ident) returns the default record's mobile payload."""
        payload = self._call()
        self.assertEqual(payload["ident"], self.default.ident)

    def test_get_with_ident_returns_matching_record(self):
        """``get(ident="default")`` returns the default record."""
        payload = self._call(ident="default")
        self.assertEqual(payload["ident"], "default")

    def test_get_with_unknown_ident_raises(self):
        """``get(ident="nonexistent")`` raises ``MissingError``."""
        with self.assertRaises(MissingError):
            self._call(ident="does-not-exist")

    def test_get_payload_has_all_expected_keys(self):
        """Wire payload matches the documented top-level key set."""
        payload = self._call()
        self.assertEqual(
            set(payload.keys()), EXPECTED_MOBILE_TOP_LEVEL_KEYS
        )

    def test_get_payload_does_not_leak_config_fields(self):
        """``/mobile-config`` MUST NOT include ``/config`` keys.

        Architectural invariant of the split: app-store metadata
        stays on its own endpoint. Regression of this test means the
        two payloads have started to overlap and should be
        re-decoupled.

        ``appName`` is an explicit exception: it appears on both
        endpoints, but they read from *different* model fields
        (``name`` on /config, ``mobile_app_name`` on /mobile-config)
        because mobile launcher labels typically differ from web app
        titles. Adding new exceptions to this set requires equally
        explicit justification.
        """
        ALLOWED_OVERLAP = {"appName"}
        payload = self._call()
        leaked = (
            set(payload.keys()) & EXPECTED_TOP_LEVEL_KEYS
        ) - ALLOWED_OVERLAP
        self.assertEqual(
            leaked,
            set(),
            "Mobile-config endpoint leaked config-only keys: %s" % leaked,
        )


class TestMonujoConfigMissingDefault(TransactionComponentCase):
    """Verify the service raises ``MissingError`` when no default exists."""

    def _call(self, **params):
        collection = self.env["lokavaluto.public.services"].browse(1)
        with collection.work_on("lcc.monujo.config") as work:
            service = work.component(usage="config")
            return service.get(**params)

    def test_to_monujo_dict_on_empty_recordset_raises(self):
        """``to_monujo_dict`` requires a single record (Odoo contract)."""
        empty = self.env["lcc.monujo.config"]
        with self.assertRaises(Exception):
            empty.to_monujo_dict()

    def test_missing_error_when_no_default(self):
        """``get()`` raises ``MissingError`` when no default is set.

        We toggle the seeded default off (rather than unlink, which
        would cascade through ~50 child records) and verify the
        service surfaces ``MissingError``.
        """
        default = self.env.ref(
            "lcc_lokavaluto_app_connection.lcc_monujo_config_default"
        )
        default.is_default = False
        try:
            with self.assertRaises(MissingError):
                self._call()
        finally:
            default.is_default = True
