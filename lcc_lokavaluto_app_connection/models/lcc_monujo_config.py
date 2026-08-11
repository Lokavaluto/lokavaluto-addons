import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class LccMonujoConfig(models.Model):
    """Server-side configuration consumed by the Monujo client.

    Replaces Monujo's bundled ``public/config.json`` so administrators
    can edit branding, theme, refresh intervals and feature toggles
    from Odoo without rebuilding the app.

    Multiple records may coexist; the Monujo client selects one by
    passing ``?ident=<ident>`` to the ``/config`` REST endpoint. When
    no ``ident`` is given, the record marked ``is_default`` is served.
    """

    _name = "lcc.monujo.config"
    _description = "Monujo App Configuration"
    _order = "sequence, ident, id"

    # -- Identity --------------------------------------------------------

    name = fields.Char(
        string="Label",
        required=True,
        help="Human-readable name (e.g. 'Default', 'Staging').",
    )
    ident = fields.Char(
        string="Identifier",
        required=True,
        help=(
            "Stable identifier passed by the Monujo client via "
            "``?ident=<value>`` to select this config."
        ),
    )
    is_default = fields.Boolean(
        string="Default config",
        help=(
            "When ``/config`` is queried without an ``ident``, "
            "the default config is served. At most one record may "
            "be marked default."
        ),
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # -- Lokapi / app endpoints ----------------------------------------

    lokapi_db = fields.Char(string="Lokapi DB")
    lokapi_host = fields.Char(string="Lokapi Host")
    map_url = fields.Char(string="Map URL")
    help_url = fields.Char(string="Help URL")
    cgu_url = fields.Char(string="CGU URL")

    # -- Branding / images ---------------------------------------------

    favicon = fields.Image(
        max_width=256,
        max_height=256,
        help="Favicon served at /web/image/lcc.monujo.config/<id>/favicon.",
    )
    logo = fields.Image(
        max_width=1024,
        max_height=1024,
        help="Main logo served at /web/image/lcc.monujo.config/<id>/logo.",
    )
    login_logo = fields.Image(
        max_width=1024,
        max_height=1024,
        help="Login screen logo served at /web/image/lcc.monujo.config/<id>/login_logo.",
    )

    # -- Theme & CSS ----------------------------------------------------

    theme_entry_ids = fields.One2many(
        "lcc.monujo.config.theme.entry",
        "config_id",
        string="Theme entries",
    )
    css = fields.Text(string="Custom CSS")

    # -- Locales --------------------------------------------------------

    locales_app_strings_language = fields.Char(
        string="App strings language",
        default="en-US",
        help="BCP-47 code of the language used as fallback for app "
        "strings (e.g. 'en-US').",
    )
    locales_default_language = fields.Char(
        string="Default language",
        default="en-US",
        help="BCP-47 code of the default UI language.",
    )
    locales_prefer_navigator_language = fields.Boolean(
        string="Prefer navigator language",
        default=True,
    )
    language_ids = fields.One2many(
        "lcc.monujo.config.language",
        "config_id",
        string="Available languages",
    )

    # -- Refresh intervals ---------------------------------------------

    accounts_refresh_interval = fields.Integer(
        string="Accounts refresh interval (s)",
        default=90,
    )
    transactions_refresh_interval = fields.Integer(
        string="Transactions refresh interval (s)",
        default=47,
    )
    currencies_refresh_interval = fields.Integer(
        string="Currencies refresh interval (s)",
        default=60,
    )

    # -- Feature toggles ------------------------------------------------

    disable_reconversion = fields.Boolean(string="Disable reconversion")
    disable_top_up = fields.Boolean(string="Disable top-up")
    disable_split_memo = fields.Boolean(string="Disable split memo")
    disable_badges = fields.Boolean(string="Disable badges")
    disable_import_wallet = fields.Boolean(string="Disable import wallet")
    disable_display_other_unpaid_topup = fields.Boolean(
        string="Disable display of other unpaid topups",
    )

    # -- Advanced -------------------------------------------------------

    local_auth_policy = fields.Text(
        string="Local auth policy (JSON)",
        help=(
            "JSON-encoded recursive policy structure consumed by the "
            "Monujo client. Example: "
            '["Retention", {"time": 900, "subConfig": ["Pin", {}]}]'
        ),
    )

    # -- Mobile app metadata -------------------------------------------
    # Served via /lokavaluto_api/public/mobile-config/, NOT /config.
    # These are app-store / launcher assets, not runtime client config.

    mobile_app_name = fields.Char(
        string="Mobile app name",
        help=(
            "Display name shown under the launcher icon on Android / "
            "iOS. Distinct from the record's ``Label`` because mobile "
            "launchers typically truncate at ~12 characters and may "
            "warrant a shorter form (e.g. 'Monujo' vs 'Monujo "
            "Lokavaluto Dev3')."
        ),
    )
    mobile_icon = fields.Image(
        max_width=1024,
        max_height=1024,
        help=(
            "App launcher / store icon for the mobile app. Served "
            "at /web/image/lcc.monujo.config/<id>/mobile_icon."
        ),
    )
    mobile_splash = fields.Image(
        max_width=2048,
        max_height=2048,
        help=(
            "Splash screen shown when the mobile app launches. "
            "Served at /web/image/lcc.monujo.config/<id>/mobile_splash."
        ),
    )
    android_play_store_app_id = fields.Char(
        string="Android Play Store app ID",
        help=(
            "Package name used by Google Play / Android intents to "
            "identify this app (e.g. 'fr.lokavaluto.monujo')."
        ),
    )
    ios_app_store_app_id = fields.Char(
        string="iOS App Store app ID",
        help=(
            "Numeric Apple App Store identifier (e.g. '1234567890') "
            "used to build itunes.apple.com URLs and StoreKit links."
        ),
    )

    # -- Constraints ----------------------------------------------------

    _sql_constraints = [
        (
            "ident_uniq",
            "unique(ident)",
            "Monujo config identifier must be unique.",
        ),
    ]

    @api.constrains("is_default")
    def _check_single_default(self):
        for rec in self:
            if not rec.is_default:
                continue
            others = self.search(
                [
                    ("is_default", "=", True),
                    ("id", "!=", rec.id),
                ]
            )
            if others:
                raise ValidationError(
                    _(
                        "Only one Monujo config may be marked default. "
                        "Currently default: %s"
                    )
                    % others[0].name
                )

    @api.constrains("local_auth_policy")
    def _check_local_auth_policy(self):
        for rec in self:
            if not rec.local_auth_policy:
                continue
            try:
                json.loads(rec.local_auth_policy)
            except json.JSONDecodeError as exc:
                raise ValidationError(
                    _("local_auth_policy is not valid JSON: %s") % exc
                )

    # -- Serialization --------------------------------------------------

    def _image_url(self, field_name, base_url=""):
        """Build the public ``/web/image/...`` URL for a Binary image
        field on this record, or return ``None`` if the field is unset.

        Args:
            field_name: Name of the ``fields.Image`` attribute.
            base_url: Optional URL prefix to prepend.

        Returns:
            str | None: Resolvable URL, or ``None`` when the image is
            empty.
        """
        self.ensure_one()
        if not self[field_name]:
            return None
        prefix = base_url.rstrip("/") if base_url else ""
        return "%s/web/image/%s/%d/%s" % (
            prefix,
            self._name,
            self.id,
            field_name,
        )

    def to_mobile_dict(self, base_url=""):
        """Serialize this config's mobile-app slice.

        Distinct from :meth:`to_monujo_dict` because the consumer is
        different: ``/mobile-config`` returns the values needed by
        app-store deep linking, mobile launchers, and splash/icon
        rendering. None of this is needed by the Monujo runtime UI,
        so we keep the two endpoints' payloads decoupled to avoid
        leaking store IDs into every page-load of the web client.

        Args:
            base_url: Optional URL prefix prepended to image URLs.

        Returns:
            dict with five keys: ``ident``, ``iconUrl``,
            ``splashUrl``, ``androidPlayStoreAppId``,
            ``iosAppStoreAppId``. URL fields are ``None`` when the
            underlying image is unset.
        """
        self.ensure_one()
        return {
            "ident": self.ident,
            "appName": self.mobile_app_name or None,
            "iconUrl": self._image_url("mobile_icon", base_url=base_url),
            "splashUrl": self._image_url("mobile_splash", base_url=base_url),
            "androidPlayStoreAppId": self.android_play_store_app_id or None,
            "iosAppStoreAppId": self.ios_app_store_app_id or None,
        }

    def to_monujo_dict(self, base_url=""):
        """Serialize this config to Monujo's wire format.

        Mirrors the shape of Monujo's ``public/config.sample.json``,
        with three additions for image fields served by Odoo:
        ``faviconUrl``, ``logoUrl`` and ``loginLogoUrl``.

        Args:
            base_url: Optional URL prefix prepended to image / file
                URLs (e.g. ``"https://odoo.example.org"``). Pass empty
                string to emit relative URLs.

        Returns:
            dict ready to be JSON-encoded as the body of
            ``GET /lokavaluto_api/public/config``.
        """
        self.ensure_one()
        base = base_url.rstrip("/") if base_url else ""

        available_languages = {}
        for lang in self.language_ids:
            entry = {"label": lang.label}
            url = lang._translation_url(base_url=base)
            if url:
                entry["url"] = url
            available_languages[lang.code] = entry

        return {
            "appName": self.name,
            "lokapiDb": self.lokapi_db or "",
            "lokapiHost": self.lokapi_host or "",
            "mapUrl": self.map_url or "",
            "helpUrl": self.help_url or "",
            "cguUrl": self.cgu_url or "",
            "logoUrl": self._image_url("logo", base_url=base),
            "loginLogoUrl": self._image_url("login_logo", base_url=base),
            "faviconUrl": self._image_url("favicon", base_url=base),
            "locales": {
                "appStringsLanguage": self.locales_app_strings_language or "",
                "defaultLanguage": self.locales_default_language or "",
                "preferNavigatorLanguage": self.locales_prefer_navigator_language,
                "availableLanguages": available_languages,
            },
            "theme": {e.key: e.value for e in self.theme_entry_ids},
            "css": self.css or "",
            "accountsRefreshInterval": self.accounts_refresh_interval,
            "transactionsRefreshInterval": self.transactions_refresh_interval,
            "currenciesRefreshInterval": self.currencies_refresh_interval,
            "disableReconversion": self.disable_reconversion,
            "disableTopUp": self.disable_top_up,
            "disableSplitMemo": self.disable_split_memo,
            "disableBadges": self.disable_badges,
            "disableImportWallet": self.disable_import_wallet,
            "disableDisplayOtherUnpaidTopup": self.disable_display_other_unpaid_topup,
            "localAuthPolicy": (
                json.loads(self.local_auth_policy)
                if self.local_auth_policy
                else None
            ),
        }
