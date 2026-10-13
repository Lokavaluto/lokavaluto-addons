import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SurveyQuestion(models.Model):
    _inherit = "survey.question"

    completion_export_key = fields.Char(
        string="Completion payload key",
        copy=False,
        groups="survey.group_survey_manager",
        help="Set to email to send this answer to the embedding page on return. "
        "Empty keys and keys other than email are not exported.",
    )

    _sql_constraints = [
        (
            "completion_export_key_unique",
            "unique(survey_id, completion_export_key)",
            "Completion payload keys must be unique within a survey.",
        ),
    ]

    @api.constrains("completion_export_key", "question_type", "is_page")
    def _check_completion_export_key(self):
        for question in self:
            # Survey officers can edit questions, but only managers can read this field.
            key = question.sudo().completion_export_key
            if not key:
                continue
            if question.is_page or question.question_type not in ("char_box", "text_box"):
                msg = _(
                    "Only text questions can be exported. Clear the completion payload "
                    "key before changing the question type."
                )
                raise ValidationError(msg)
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", key) or key in (
                "constructor",
                "prototype",
                "survey_token",
                "answer_token",
                "access_token",
            ):
                msg = _(
                    "Use a unique payload key beginning with a letter, followed by "
                    "letters, numbers or underscores (maximum 64 characters). "
                    "Token and object-property names are reserved."
                )
                raise ValidationError(msg)
