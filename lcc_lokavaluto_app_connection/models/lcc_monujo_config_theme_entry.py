from odoo import fields, models


class LccMonujoConfigThemeEntry(models.Model):
    """A single theme key/value pair attached to a ``lcc.monujo.config``.

    Stored as rows rather than as columns or a JSON blob so the admin
    UI can edit each entry inline, and Odoo's standard CRUD applies
    (search, copy on duplicate, etc.).
    """

    _name = "lcc.monujo.config.theme.entry"
    _description = "Monujo Config — Theme Entry"
    _order = "sequence, key, id"

    config_id = fields.Many2one(
        "lcc.monujo.config",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    key = fields.Char(required=True)
    value = fields.Char(required=True)

    _sql_constraints = [
        (
            "config_key_uniq",
            "unique(config_id, key)",
            "Theme key must be unique within a Monujo config.",
        ),
    ]
