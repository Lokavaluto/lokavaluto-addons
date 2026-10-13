from urllib.parse import parse_qsl, urlsplit

from odoo import _, http
from odoo.http import request

from odoo.addons.survey.controllers.main import Survey

from ..utils import completion_options, origin, with_query


class SurveyCompletionAction(Survey):
    @http.route()
    def survey_start(self, survey_token, answer_token=None, email=False, **post):
        response = super().survey_start(
            survey_token, answer_token=answer_token, email=email, **post
        )
        # Inspect the original query: Odoo flattens duplicate parameters in post.
        options = completion_options(request.httprequest.args)
        location = response.headers.get("Location")
        if options and location:
            parts = urlsplit(location)
            if (
                not parts.scheme
                and not parts.netloc
                and parts.path.startswith(f"/survey/{survey_token}/")
            ):
                response.headers["Location"] = with_query(location, options)
        return response

    def _redirect_with_error(self, access_data, error_key):
        response = super()._redirect_with_error(access_data, error_key)
        options = completion_options(request.httprequest.args)
        if error_key == "survey_auth" and options and response.qcontext:
            # Preserve the nested survey destination in Odoo's login/signup URL.
            login_url = response.qcontext.get("redirect_url")
            if login_url:
                destination = dict(parse_qsl(urlsplit(login_url).query)).get("redirect")
                expected_path = f"/survey/start/{access_data['survey_sudo'].access_token}"
                if destination and urlsplit(destination).path == expected_path:
                    response.qcontext["redirect_url"] = with_query(
                        login_url, {"redirect": with_query(destination, options)}
                    )
        return response

    @http.route(
        "/survey/completion_action/<string:survey_token>/<string:answer_token>",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def survey_completion_action(self, survey_token, answer_token, **post):
        """Resolve an opt-in action only after normal survey access checks."""
        options = completion_options(post)
        if not options:
            return {}
        access = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access["validity_code"] is not True or access["answer_sudo"].state != "done":
            return {}
        parent_origin = origin(options["parent_origin"])
        if not parent_origin:
            return {}
        return {
            "label": options.get("return_label", "").strip() or _("Continue"),
            "parent_origin": parent_origin,
            "payload": access["answer_sudo"]._completion_payload(),
        }
