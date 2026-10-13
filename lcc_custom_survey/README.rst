Custom Survey
=============

An Odoo 16 extension of standard Survey. Existing and future surveys can show an
optional completion button. Clicking it sends a return message to the parent
page when the survey is inside an iframe, with the answer mapped as ``email``.
There is no origin allowlist. The parent decides whether to navigate.
Outside an iframe, the button stays hidden. No particular application, survey,
stylesheet or business workflow is required.

Installation
------------

Place ``lcc_custom_survey`` in an Odoo 16 addons directory, restart Odoo, update
the Apps list, and install "Custom Survey". Remove the Apps filter when searching:
this is an extension, not a standalone application. Its standard ``survey``
dependency is installed automatically if needed.

Alternatively, install it using your normal Odoo configuration::

    odoo -c /path/to/odoo.conf -d DATABASE -i lcc_custom_survey --stop-after-init

Configuration
-------------

A survey manager opens the email question's Options tab and sets its Completion
payload key to ``email``. Only that key is exported. Empty keys and other existing
keys, such as ``reference``, are ignored. If no email answer is mapped, or it is
empty, skipped or invalid, the return message has an empty payload. Email values
are trimmed, limited to 254 characters, and checked for a basic email format
without control characters before leaving Odoo.

Single-line and multi-line text questions are supported. Keys remain unique
within a survey, and copying a question clears its key. No destination settings
are needed: any embedding HTTP(S) origin can receive the email when the
participant clicks the completion button.

URL and message contract
------------------------

* ``parent_origin`` enables the button inside an iframe and identifies the recipient.
  It must be an exact HTTP(S) origin, without a path, credentials or wildcard.
* ``return_label`` optionally overrides the translated default, "Continue".
  The label is plain text, limited to 120 characters.

Without ``parent_origin``, the survey has no extra button and makes no completion
payload request. Repeated completion parameters are rejected. There is no mode
selector or destination URL: the addon never navigates the browser itself.

Install the parent's listener before setting the iframe URL, and remove it on
unmount. Build URLs with a URL builder so parameters are encoded correctly::

    const survey = new URL('/survey/start/SURVEY_TOKEN', ODOO_ORIGIN);
    survey.searchParams.set('parent_origin', window.location.origin);
    survey.searchParams.set('return_label', 'Return');
    function onMessage(event) {
        if (event.origin !== survey.origin) return;
        if (event.source !== iframe.contentWindow) return;
        if (event.data?.type !== 'odoo:survey:return') return;
        onReturnRequested(event.data.payload || {});
    }
    window.addEventListener('message', onMessage);
    iframe.src = survey.href;
    // On unmount: window.removeEventListener('message', onMessage);

The message is ``{type: 'odoo:survey:return', payload: {email: 'alice@example.org'}}``.
The payload is empty when no mapped, non-empty email answer is available from the
current completed attempt. No other answer keys are sent. The receiver chooses
the navigation and validates the email before using it. This is a user navigation
request, not proof of identity, account creation, approval, payment or any
business transaction.

Behavior and limits
-------------------

The button appears only inside an iframe on a completed attempt, including failed
scored attempts, and only after the server validates access and the recipient's
origin format. Invalid options or unavailable completion data leave it hidden. Submission
alone sends no parent message: the participant must click the button. An empty
payload still tells the parent that the participant requested a return from a
completed survey; it does not certify that the parent application is trustworthy.

The same URL can be opened directly in a browser tab. The completion button stays
hidden and no completion payload request is made, even with a valid
``parent_origin`` in the URL.

No action settings are saved on the attempt or in a shared session. They survive
the start redirect, AJAX steps, reloads, standard Odoo login/signup return URLs
and retry/review links. A fresh link without options stays inactive. External SSO
flows that replace Odoo's return URL may need their own integration.

No other answers or access tokens are included in the payload.
An exact ``postMessage`` target prevents delivery to a different origin, but it
does not establish trust: any site allowed to embed the survey can request the
mapped email. The frontend requests that email from Odoo after completion;
it sends it to the parent only on a button click. Answer values
are user-supplied suggestions, never authentication credentials. Embedding still
requires suitable deployment headers, HTTPS and iframe sandbox permissions; this
addon does not change them. Standard Odoo 16 survey rendering is supported.
Custom replacement completion screens may require adaptation.

Upgrading from the two-mode prototype
----------------------------------------

Update the addon and its embedding application together, then reload open survey
pages. Use ``parent_origin`` to activate the feature; ``return_mode`` and
``return_url`` are ignored. Direct redirects and answer export through a
destination URL are removed. The Survey Completion origin settings and their
interface have been removed. Old ``lcc_custom_survey.message_origins`` and
``lcc_custom_survey.redirect_origins`` values are ignored. Existing ``email``
mappings keep working; other mapped keys are no longer exported.

Manual verification
-------------------

* Open a survey without parameters: finish normally without an extra button.
* Embed it with a valid ``parent_origin``: finish, click the button, and check
  that the parent receives only the mapped email.
* Open that configured URL in its own tab: no extra button or completion payload request.
* Check that missing, blank or skipped email answers produce an empty payload.
* Check that malformed origins are rejected and other mapped answers stay private.
* Check that reloads, login and retry preserve valid options.

Tests cover email-only sharing, legacy settings being ignored, empty payloads,
survey access checks and option preservation through start, login and retry. Run them on a test database with Odoo's test runner
and ``--test-tags /lcc_custom_survey``. Demo surveys are maintained separately.

The frontend regression tests run without an Odoo server::

    node lcc_custom_survey/tests/survey_completion.test.cjs
