from odoo import models

from ..utils import completion_email


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    def _completion_payload(self):
        """Export only the text answer mapped as email from this completed attempt."""
        self.ensure_one()
        if self.state != "done":
            return {}
        for line in self.user_input_line_ids:
            question = line.question_id
            key = question.completion_export_key
            if key != "email" or line.skipped or question.survey_id != self.survey_id:
                continue
            if question.question_type == line.answer_type == "char_box":
                value = line.value_char_box
            elif question.question_type == line.answer_type == "text_box":
                value = line.value_text_box
            else:
                continue
            email = completion_email(value)
            if email:
                return {"email": email}
        return {}
