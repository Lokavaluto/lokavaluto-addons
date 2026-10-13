odoo.define('lcc_custom_survey.survey_completion', function (require) {
    'use strict';

    const SurveyFormWidget = require('survey.form');
    const OPTION_KEYS = ['parent_origin', 'return_label'];

    function getOptions() {
        // Standalone surveys must not show a return button or request a payload.
        if (window.parent === window) {
            return null;
        }
        const params = new URLSearchParams(window.location.search);
        if (!params.get('parent_origin')) {
            return null;
        }
        const options = {};
        for (const key of OPTION_KEYS) {
            if (params.getAll(key).length > 1) {
                return null;
            }
            if (params.has(key)) {
                options[key] = params.get(key);
            }
        }
        return options;
    }

    SurveyFormWidget.include({
        events: Object.assign({}, SurveyFormWidget.prototype.events, {
            'click .o_survey_completion_button': '_onCompletionAction',
        }),

        start: function () {
            return this._super.apply(this, arguments).then(() => this._refreshCompletionAction());
        },

        _onNextScreenDone: function () {
            const result = this._super.apply(this, arguments);
            this._refreshCompletionAction();
            return result;
        },

        _refreshCompletionAction: function () {
            this._completionAction = null;
            const generation = this._completionGeneration = (this._completionGeneration || 0) + 1;
            this.$('.o_survey_completion_action').addClass('d-none');
            const options = getOptions();
            if (!options || !this.$('.o_survey_finished').length) {
                return Promise.resolve();
            }

            // Retry and review links leave the AJAX flow; retain this tab's options.
            this.$('.o_survey_finished a[href]').each(function () {
                const url = new URL(this.href, window.location.href);
                if (url.origin === window.location.origin && /^\/survey\/(retry|print)\//.test(url.pathname)) {
                    for (const [key, value] of Object.entries(options)) {
                        url.searchParams.set(key, value);
                    }
                    this.href = url.href;
                }
            });

            return this._rpc({
                route: `/survey/completion_action/${this.options.surveyToken}/${this.options.answerToken}`,
                params: options,
            }).then(action => {
                if (this.isDestroyed() || generation !== this._completionGeneration ||
                    !this.$('.o_survey_finished').length) {
                    return;
                }
                if (!action || !action.parent_origin) {
                    return;
                }
                this._completionAction = action;
                this.$('.o_survey_completion_button').text(action.label);
                this.$('.o_survey_completion_action').removeClass('d-none');
            }).catch(() => {
                // A failed optional action must not interrupt a completed survey.
            });
        },

        _onCompletionAction: function (event) {
            event.preventDefault();
            const action = this._completionAction;
            if (!action || !this.$('.o_survey_finished').length || window.parent === window) {
                return;
            }
            window.parent.postMessage({
                type: 'odoo:survey:return',
                payload: action.payload || {},
            }, action.parent_origin);
        },
    });
});
