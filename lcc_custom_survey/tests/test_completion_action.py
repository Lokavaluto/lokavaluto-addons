import json
from urllib.parse import parse_qs, urlencode, urlsplit

from lxml import html
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestCompletionAction(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.survey = cls.env["survey.survey"].create({
            "title": "Completion sharing test",
            "access_mode": "public",
            "questions_layout": "one_page",
            "users_login_required": False,
        })
        cls.email_question = cls.env["survey.question"].create({
            "survey_id": cls.survey.id,
            "title": "Email",
            "question_type": "char_box",
            "completion_export_key": "email",
        })
        cls.private_question = cls.env["survey.question"].create({
            "survey_id": cls.survey.id,
            "title": "Private answer",
            "question_type": "char_box",
        })
        cls.answer = cls.env["survey.user_input"].create({
            "survey_id": cls.survey.id,
            "state": "done",
        })
        for question, value in (
            (cls.email_question, "alice@example.org"),
            (cls.private_question, "Do not export this answer"),
        ):
            cls.env["survey.user_input.line"].create({
                "user_input_id": cls.answer.id,
                "question_id": question.id,
                "answer_type": "char_box",
                "value_char_box": value,
            })

    def _action(self, params=None, survey_token=None, answer_token=None):
        self.env.flush_all()
        response = self.url_open(
            "/survey/completion_action/%s/%s" % (
                survey_token or self.survey.access_token,
                answer_token or self.answer.access_token,
            ),
            data=json.dumps({"jsonrpc": "2.0", "method": "call", "id": 1, "params": params or {}}),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        result = response.json()
        self.assertNotIn("error", result)
        return result["result"]

    def test_parent_receives_email(self):
        action = self._action({
            "parent_origin": "https://APP.example:443/", "return_label": "Back to login",
        })
        self.assertEqual(action, {
            "parent_origin": "https://app.example",
            "label": "Back to login",
            "payload": {"email": "alice@example.org"},
        })

    def test_legacy_allowlist_has_no_effect(self):
        for configured in ("", "https://app.example"):
            with self.subTest(configured=configured):
                self.env["ir.config_parameter"].sudo().set_param(
                    "lcc_custom_survey.message_origins", configured,
                )
                action = self._action({"parent_origin": "https://other.example"})
                self.assertEqual(action["parent_origin"], "https://other.example")
                self.assertEqual(action["payload"], {"email": "alice@example.org"})

    def test_other_mapped_answers_are_never_exported(self):
        self.private_question.completion_export_key = "reference"
        action = self._action({"parent_origin": "https://app.example"})
        self.assertEqual(action["payload"], {"email": "alice@example.org"})

    def test_missing_email_mapping_returns_empty_payload(self):
        self.email_question.completion_export_key = False
        action = self._action({"parent_origin": "https://app.example"})
        self.assertTrue(action["label"])
        self.assertEqual(action["payload"], {})

    def test_empty_or_skipped_email_is_not_exported(self):
        line = self.answer.user_input_line_ids.filtered(
            lambda answer: answer.question_id == self.email_question
        )
        for values in (
            {"value_char_box": "   "},
            {"value_char_box": False, "answer_type": False, "skipped": True},
        ):
            with self.subTest(values=values):
                line.write(values)
                action = self._action({"parent_origin": "https://app.example"})
                self.assertEqual(action["payload"], {})

    def test_invalid_email_answers_are_not_exported(self):
        line = self.answer.user_input_line_ids.filtered(
            lambda answer: answer.question_id == self.email_question
        )
        for value in ("not an email", "alice@example.org\nprivate note", "a" * 250 + "@example.org"):
            with self.subTest(value=value):
                line.value_char_box = value
                self.assertEqual(self._action({"parent_origin": "https://app.example"})["payload"], {})
        line.value_char_box = "  alice+survey@example.org  "
        self.assertEqual(
            self._action({"parent_origin": "https://app.example"})["payload"],
            {"email": "alice+survey@example.org"},
        )

    def test_multiline_email_question(self):
        self.email_question.question_type = "text_box"
        self.answer.user_input_line_ids.filtered(
            lambda answer: answer.question_id == self.email_question
        ).write({"answer_type": "text_box", "value_text_box": "alice@example.org"})
        self.assertEqual(
            self._action({"parent_origin": "https://app.example"})["payload"],
            {"email": "alice@example.org"},
        )

    def test_answer_from_another_survey_is_rejected(self):
        other = self.survey.copy()
        self.assertEqual(self._action(
            {"parent_origin": "https://app.example"}, survey_token=other.access_token,
        ), {})

    def test_start_preserves_options_without_exposing_email(self):
        options = {"parent_origin": "https://app.example", "return_label": "Retour à la connexion"}
        response = self.url_open("/survey/start/%s?%s" % (
            self.survey.access_token,
            urlencode({"answer_token": self.answer.access_token, **options}),
        ))
        response.raise_for_status()
        self.assertEqual(parse_qs(urlsplit(response.url).query), {
            key: [value] for key, value in options.items()
        })
        self.assertNotIn("alice@example.org", response.url)

    def test_duplicate_options_are_dropped_on_start(self):
        response = self.url_open("/survey/start/%s?%s" % (
            self.survey.access_token,
            urlencode([
                ("answer_token", self.answer.access_token),
                ("parent_origin", "https://app.example"),
                ("parent_origin", "https://other.example"),
            ]),
        ))
        response.raise_for_status()
        self.assertEqual(urlsplit(response.url).query, "")

    def test_retry_preserves_options_with_a_new_attempt(self):
        options = {"parent_origin": "https://app.example", "return_label": "Return"}
        response = self.url_open("/survey/retry/%s/%s?%s" % (
            self.survey.access_token, self.answer.access_token, urlencode(options),
        ))
        response.raise_for_status()
        self.assertEqual(parse_qs(urlsplit(response.url).query), {
            key: [value] for key, value in options.items()
        })
        self.assertNotIn(self.answer.access_token, urlsplit(response.url).path)
        self.assertTrue(urlsplit(response.url).path.startswith("/survey/%s/" % self.survey.access_token))

    def test_login_link_preserves_options_and_answer_token(self):
        self.survey.users_login_required = True
        self.env.flush_all()
        options = {"parent_origin": "https://app.example", "return_label": "Return"}
        response = self.url_open("/survey/start/%s?%s" % (
            self.survey.access_token,
            urlencode({"answer_token": self.answer.access_token, **options}),
        ))
        response.raise_for_status()
        links = html.fromstring(response.content).xpath('//a[contains(@href, "/web/login?")]/@href')
        self.assertTrue(links)
        destination = parse_qs(urlsplit(links[0]).query)["redirect"][0]
        self.assertEqual(urlsplit(destination).path, "/survey/start/%s" % self.survey.access_token)
        self.assertEqual(parse_qs(urlsplit(destination).query), {
            key: [value] for key, value in {"answer_token": self.answer.access_token, **options}.items()
        })

    def test_invalid_options_do_not_enable_return(self):
        for params in (
            {}, {"parent_origin": "null"}, {"parent_origin": "*"},
            {"parent_origin": "https://app.example/path"},
            {"parent_origin": "https://app.example", "return_label": "x" * 121},
        ):
            with self.subTest(params=params):
                self.assertEqual(self._action(params), {})

    def test_invalid_tokens_do_not_enable_return(self):
        params = {"parent_origin": "https://other.example"}
        self.assertEqual(self._action(params, answer_token="invalid"), {})
        self.assertEqual(self._action(params, survey_token="invalid"), {})

    def test_unfinished_attempt_does_not_enable_return(self):
        self.answer.state = "in_progress"
        for recipient in ("https://app.example", "https://other.example"):
            with self.subTest(recipient=recipient):
                self.assertEqual(self._action({"parent_origin": recipient}), {})

    def test_login_required_still_blocks_public_return(self):
        self.survey.users_login_required = True
        self.assertEqual(self._action({"parent_origin": "https://other.example"}), {})
