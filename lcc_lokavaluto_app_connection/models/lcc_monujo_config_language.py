from odoo import fields, models


class LccMonujoConfigLanguage(models.Model):
    """An available language entry attached to a ``lcc.monujo.config``.

    Reuses Odoo's ``res.lang`` registry for code + display name. The
    optional ``translation_file`` (a binary attachment) is exposed at
    ``/web/content/<attachment-id>`` so the Monujo client can fetch
    the compiled i18n JSON bundle.

    Languages with no ``translation_file`` are valid: the Monujo app
    is expected to bundle a default language (English) at build time;
    such an entry tells the client "this language is available" without
    pointing to a URL.
    """

    _name = "lcc.monujo.config.language"
    _description = "Monujo Config — Available Language"
    _order = "lang_id, id"

    config_id = fields.Many2one(
        "lcc.monujo.config",
        required=True,
        ondelete="cascade",
        index=True,
    )
    lang_id = fields.Many2one(
        "res.lang",
        required=True,
        string="Language",
        help="Reuses Odoo's language registry (code + display name).",
    )
    # Read-through helpers for the REST serializer
    code = fields.Char(
        related="lang_id.code",
        store=False,
        readonly=True,
        string="Code",
    )
    label = fields.Char(
        related="lang_id.name",
        store=False,
        readonly=True,
        string="Label",
    )

    translation_file = fields.Binary(
        attachment=True,
        string="Translation file",
        help=(
            "Compiled i18n JSON bundle (e.g. fr-FR.json). "
            "Leave empty if the language is shipped inside the app "
            "(e.g. English)."
        ),
    )
    translation_filename = fields.Char(string="Filename")

    _sql_constraints = [
        (
            "config_lang_uniq",
            "unique(config_id, lang_id)",
            "Each language may appear at most once per Monujo config.",
        ),
    ]

    def _translation_url(self, base_url=""):
        """Return the URL serving ``translation_file``, or ``None``.

        Args:
            base_url: Optional URL prefix (e.g. ``"https://odoo.example.org"``).

        Returns:
            str | None: A URL pointing to the bundled translation file
            on Odoo's ``/web/content`` route, or ``None`` if no file is
            attached.
        """
        self.ensure_one()
        if not self.translation_file:
            return None
        attachment = (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", self.id),
                    ("res_field", "=", "translation_file"),
                ],
                limit=1,
            )
        )
        if not attachment:
            return None
        prefix = base_url.rstrip("/") if base_url else ""
        return "%s/web/content/%d?download=true" % (prefix, attachment.id)
