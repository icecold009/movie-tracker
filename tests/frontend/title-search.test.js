"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const { JSDOM } = require("jsdom");

const {
    ERROR_MESSAGES,
    SEARCH_DEBOUNCE_MS,
    setupTitleSearch
} = require("../../static/title-search.js");

class Scheduler {
    constructor() {
        this.nextId = 1;
        this.tasks = new Map();
    }

    setTimeout(callback, delay) {
        const id = this.nextId;
        this.nextId += 1;
        this.tasks.set(id, { callback: callback, delay: delay });
        return id;
    }

    clearTimeout(id) {
        this.tasks.delete(id);
    }

    runNext() {
        const entry = this.tasks.entries().next();
        assert.equal(entry.done, false, "expected a scheduled search");
        const [id, task] = entry.value;
        this.tasks.delete(id);
        task.callback();
        return task.delay;
    }
}

function deferred() {
    let resolve;
    let reject;
    const promise = new Promise(function (resolvePromise, rejectPromise) {
        resolve = resolvePromise;
        reject = rejectPromise;
    });
    return { promise: promise, reject: reject, resolve: resolve };
}

function response(payload, options) {
    const settings = options || {};
    return {
        ok: settings.ok !== false,
        status: settings.status || 200,
        json: async function () {
            if (settings.jsonError) {
                throw settings.jsonError;
            }
            return payload;
        }
    };
}

function createHarness(t, fetchSearch) {
    const dom = new JSDOM(`<!doctype html>
        <input id="title" maxlength="200">
        <div id="title-search-feedback" hidden></div>
        <div id="title-search-results" hidden></div>`);
    const scheduler = new Scheduler();
    const search = setupTitleSearch({
        AbortController: dom.window.AbortController,
        clearTimeout: scheduler.clearTimeout.bind(scheduler),
        document: dom.window.document,
        fetch: fetchSearch,
        setTimeout: scheduler.setTimeout.bind(scheduler),
        window: dom.window
    });
    t.after(function () {
        search.destroy();
        dom.window.close();
    });
    return {
        feedback: dom.window.document.getElementById("title-search-feedback"),
        input: dom.window.document.getElementById("title"),
        results: dom.window.document.getElementById("title-search-results"),
        scheduler: scheduler,
        window: dom.window
    };
}

function type(harness, value) {
    harness.input.value = value;
    harness.input.dispatchEvent(new harness.window.Event("input", { bubbles: true }));
}

async function flushPromises() {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
}

test("browser global initializes from window defaults", function (t) {
    const dom = new JSDOM(`<!doctype html>
        <input id="title">
        <div id="title-search-feedback" hidden></div>
        <div id="title-search-results" hidden></div>`, {
        runScripts: "outside-only",
        url: "http://localhost/"
    });
    dom.window.fetch = async function () {
        return response({ result: null });
    };
    const source = fs.readFileSync(
        path.join(__dirname, "..", "..", "static", "title-search.js"),
        "utf8"
    );
    dom.window.eval(source);

    const search = dom.window.MovieTrackerTitleSearch.setupTitleSearch();

    assert.ok(search);
    t.after(function () {
        search.destroy();
        dom.window.close();
    });
});

test("debounces title input and only searches the latest query", async function (t) {
    const calls = [];
    const harness = createHarness(t, async function (url) {
        calls.push(url);
        return response({ result: null });
    });

    type(harness, "du");
    type(harness, "dune");

    assert.equal(harness.scheduler.tasks.size, 1);
    assert.equal(harness.scheduler.runNext(), SEARCH_DEBOUNCE_MS);
    await flushPromises();
    assert.deepEqual(calls, ["/search?q=dune"]);
});

test("aborts an in-flight request when the query changes", function (t) {
    const requests = [];
    const harness = createHarness(t, function (url, options) {
        requests.push({ options: options, url: url });
        return new Promise(function () {});
    });

    type(harness, "du");
    harness.scheduler.runNext();
    assert.equal(requests[0].options.signal.aborted, false);

    type(harness, "dune");

    assert.equal(requests[0].options.signal.aborted, true);
    assert.equal(harness.feedback.dataset.state, "pending");
});

test("ignores an older response even when its fetch does not honor abort", async function (t) {
    const requests = [];
    const harness = createHarness(t, function (url) {
        const pending = deferred();
        requests.push({ pending: pending, url: url });
        return pending.promise;
    });

    type(harness, "du");
    harness.scheduler.runNext();
    type(harness, "dune");
    harness.scheduler.runNext();

    requests[1].pending.resolve(response({ result: { full_title: "Dune" } }));
    await flushPromises();
    assert.match(harness.results.textContent, /Dune/);

    requests[0].pending.resolve(response({ result: { full_title: "Old result" } }));
    await flushPromises();
    assert.match(harness.results.textContent, /Dune/);
    assert.doesNotMatch(harness.results.textContent, /Old result/);
});

test("clearing input aborts and invalidates the pending response", async function (t) {
    const pending = deferred();
    let signal;
    const harness = createHarness(t, function (url, options) {
        signal = options.signal;
        return pending.promise;
    });

    type(harness, "dune");
    harness.scheduler.runNext();
    type(harness, "");

    assert.equal(signal.aborted, true);
    assert.equal(harness.feedback.hidden, true);
    assert.equal(harness.feedback.dataset.state, "idle");
    assert.equal(harness.results.hidden, true);

    pending.resolve(response({ result: { full_title: "Dune" } }));
    await flushPromises();
    assert.equal(harness.results.textContent, "");
});

test("renders an explicit no-result state", async function (t) {
    const harness = createHarness(t, async function () {
        return response({ result: null });
    });

    type(harness, "unknown title");
    harness.scheduler.runNext();
    await flushPromises();

    assert.equal(harness.feedback.dataset.state, "empty");
    assert.match(harness.feedback.textContent, /No TMDB match found/);
    assert.equal(harness.results.hidden, true);
});

test("selection copies the matched title and hides the result", async function (t) {
    const harness = createHarness(t, async function () {
        return response({ result: { full_title: "Dune: Part Two" } });
    });

    type(harness, "dune");
    harness.scheduler.runNext();
    await flushPromises();
    harness.results.querySelector("button").click();

    assert.equal(harness.input.value, "Dune: Part Two");
    assert.equal(harness.feedback.dataset.state, "selected");
    assert.equal(harness.results.hidden, true);
});

test("maps each server failure code to a distinct visible state", async function (t) {
    const cases = [
        ["timeout", 503],
        ["rate_limited", 429],
        ["provider_unavailable", 503],
        ["malformed_response", 503]
    ];

    for (const [code, status] of cases) {
        await t.test(code, async function (subtest) {
            const harness = createHarness(subtest, async function () {
                return response(
                    { error: "Safe provider error.", error_code: code, retryable: true },
                    { ok: false, status: status }
                );
            });

            type(harness, "dune");
            harness.scheduler.runNext();
            await flushPromises();

            assert.equal(harness.feedback.dataset.state, `error-${code}`);
            assert.equal(harness.feedback.textContent, ERROR_MESSAGES[code]);
            assert.equal(harness.results.querySelector(".search-retry").textContent, "Retry search");
        });
    }
});

test("maps a rejected browser fetch to the offline state", async function (t) {
    const harness = createHarness(t, async function () {
        throw new TypeError("fetch failed");
    });

    type(harness, "dune");
    harness.scheduler.runNext();
    await flushPromises();

    assert.equal(harness.feedback.dataset.state, "error-offline");
    assert.equal(harness.feedback.textContent, ERROR_MESSAGES.offline);
});

test("clears the last good result while a newer request is pending or fails", async function (t) {
    const second = deferred();
    let requestCount = 0;
    const harness = createHarness(t, function () {
        requestCount += 1;
        if (requestCount === 1) {
            return Promise.resolve(response({ result: { full_title: "Dune" } }));
        }
        return second.promise;
    });

    type(harness, "dune");
    harness.scheduler.runNext();
    await flushPromises();
    assert.match(harness.results.textContent, /Dune/);

    type(harness, "arrival");
    assert.equal(harness.results.textContent, "");
    assert.equal(harness.results.hidden, true);
    harness.scheduler.runNext();
    second.resolve(response(
        { error: "TMDB took too long.", error_code: "timeout", retryable: true },
        { ok: false, status: 503 }
    ));
    await flushPromises();

    assert.doesNotMatch(harness.results.textContent, /Dune/);
    assert.equal(harness.feedback.dataset.state, "error-timeout");
});

test("retry transitions immediately to retrying and can render a result", async function (t) {
    let requestCount = 0;
    const harness = createHarness(t, async function () {
        requestCount += 1;
        if (requestCount === 1) {
            return response(
                { error: "Unavailable.", error_code: "provider_unavailable", retryable: true },
                { ok: false, status: 503 }
            );
        }
        return response({ result: { full_title: "Dune" } });
    });

    type(harness, "dune");
    harness.scheduler.runNext();
    await flushPromises();
    harness.results.querySelector(".search-retry").click();

    assert.equal(harness.feedback.dataset.state, "retrying");
    assert.equal(harness.scheduler.runNext(), 0);
    await flushPromises();
    assert.equal(requestCount, 2);
    assert.equal(harness.feedback.dataset.state, "success");
    assert.match(harness.results.textContent, /Dune/);
});
