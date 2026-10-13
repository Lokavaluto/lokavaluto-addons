const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const source = readFileSync(path.join(__dirname, '../static/src/js/survey_completion.js'), 'utf8');

// Exercise the actual widget extension without requiring an Odoo browser server.
function setup({ embedded = true, query = '?parent_origin=https%3A%2F%2Fapp.example', finished = true } = {}) {
    let extension;
    const calls = [];
    const messages = [];
    const state = { hidden: true, label: '', finished, destroyed: false, links: [] };
    const window = {
        location: { search: query, origin: 'https://odoo.example', href: `https://odoo.example/survey/s/a${query}` },
        postMessage: (...args) => messages.push(args),
    };
    window.parent = embedded ? { postMessage: (...args) => messages.push(args) } : window;
    vm.runInNewContext(source, {
        window, URL, URLSearchParams,
        odoo: { define: (_name, factory) => factory(() => ({
            prototype: { events: {} },
            include: value => { extension = value; },
        })) },
    });
    const widget = {
        ...extension,
        options: { surveyToken: 's', answerToken: 'a' },
        isDestroyed: () => state.destroyed,
        _rpc(request) {
            return new Promise((resolve, reject) => calls.push({ request, resolve, reject }));
        },
        $(selector) {
            if (selector === '.o_survey_finished') return { length: Number(state.finished) };
            if (selector === '.o_survey_finished a[href]') return {
                each: callback => state.links.forEach(link => callback.call(link)),
            };
            return {
                addClass: () => { state.hidden = true; },
                removeClass: () => { state.hidden = false; },
                text: value => { state.label = value; },
            };
        },
    };
    return { widget, calls, messages, state };
}

const action = {
    label: 'Back to login', parent_origin: 'https://app.example',
    payload: { email: 'alice@example.org' },
};
const click = widget => widget._onCompletionAction({ preventDefault() {} });

test('standalone, unfinished, missing and duplicate options never fetch or send answers', async () => {
    for (const options of [
        { embedded: false }, { finished: false }, { query: '' },
        { query: '?parent_origin=https://a.example&parent_origin=https://b.example' },
        { query: '?parent_origin=https://a.example&return_label=A&return_label=B' },
    ]) {
        const { widget, calls, messages, state } = setup(options);
        await widget._refreshCompletionAction();
        click(widget);
        assert.equal(calls.length, 0);
        assert.equal(messages.length, 0);
        assert.equal(state.hidden, true);
    }
});

test('completion sends only on a click and uses the exact target origin', async () => {
    const { widget, calls, messages, state } = setup();
    const refresh = widget._refreshCompletionAction();
    assert.equal(calls[0].request.route, '/survey/completion_action/s/a');
    calls[0].resolve(action);
    await refresh;
    assert.equal(state.hidden, false);
    assert.equal(state.label, action.label);
    assert.equal(messages.length, 0);
    click(widget);
    assert.deepEqual(JSON.parse(JSON.stringify(messages)), [[{
        type: 'odoo:survey:return', payload: action.payload,
    }, action.parent_origin]]);
});

test('a failed or refused optional request keeps the action hidden', async () => {
    for (const fail of [false, true]) {
        const { widget, calls, messages, state } = setup();
        const refresh = widget._refreshCompletionAction();
        if (fail) calls[0].reject(new Error('offline'));
        else calls[0].resolve({});
        await refresh;
        click(widget);
        assert.equal(state.hidden, true);
        assert.equal(messages.length, 0);
    }
});

test('a stale response cannot restore a button after leaving the completion screen', async () => {
    const { widget, calls, state } = setup();
    const refresh = widget._refreshCompletionAction();
    state.finished = false;
    await widget._refreshCompletionAction();
    calls[0].resolve(action);
    await refresh;
    assert.equal(state.hidden, true);
    assert.equal(widget._completionAction, null);
});

test('responses after destruction are ignored', async () => {
    const { widget, calls, state } = setup();
    const refresh = widget._refreshCompletionAction();
    state.destroyed = true;
    calls[0].resolve(action);
    await refresh;
    assert.equal(state.hidden, true);
});

test('retry and review links keep options without modifying unrelated links', async () => {
    const { widget, calls, state } = setup();
    state.links = [
        { href: 'https://odoo.example/survey/retry/s/a?language=fr' },
        { href: 'https://odoo.example/survey/print/s?answer_token=a' },
        { href: 'https://other.example/survey/retry/s/a' },
    ];
    const refresh = widget._refreshCompletionAction();
    calls[0].resolve(action);
    await refresh;
    assert.equal(new URL(state.links[0].href).searchParams.get('parent_origin'), action.parent_origin);
    assert.equal(new URL(state.links[0].href).searchParams.get('language'), 'fr');
    assert.equal(new URL(state.links[1].href).searchParams.get('answer_token'), 'a');
    assert.equal(new URL(state.links[1].href).searchParams.get('parent_origin'), action.parent_origin);
    assert.equal(state.links[2].href, 'https://other.example/survey/retry/s/a');
});
