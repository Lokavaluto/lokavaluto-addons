# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Custom Survey",
    "version": "16.0.1.3.1",
    "author": "Lokavaluto",
    "website": "https://lokavaluto.fr",
    "license": "AGPL-3",
    "category": "Marketing/Surveys",
    "summary": "Optional survey completion message with email",
    "depends": ["survey"],
    "data": [
        "views/survey_question_views.xml",
        "views/survey_templates.xml",
    ],
    "assets": {
        "survey.survey_assets": [
            "lcc_custom_survey/static/src/js/survey_completion.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}
