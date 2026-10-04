(function (root, factory) {
    "use strict";

    const api = factory(root);
    if (typeof module === "object" && module.exports) {
        module.exports = api;
    }
    if (root) {
        root.MovieTrackerTitleSearch = api;
    }
}(typeof window !== "undefined" ? window : null, function (defaultWindow) {
    "use strict";

    const SEARCH_DEBOUNCE_MS = 260;
    const ERROR_MESSAGES = {
        timeout: "TMDB took too long to respond. Retry the search or save manually.",
        offline: "You appear to be offline. Reconnect and retry, or save manually.",
        rate_limited: "TMDB search is rate-limited. Wait a moment, then retry or save manually.",
        provider_unavailable: "TMDB search is temporarily unavailable. Retry the search or save manually.",
        malformed_response: "TMDB returned an unexpected response. Retry the search or save manually."
    };

    function normalizeErrorCode(code, status) {
        if (Object.hasOwn(ERROR_MESSAGES, code)) {
            return code;
        }
        return status === 429 ? "rate_limited" : "provider_unavailable";
    }

    function searchError(code, retryable) {
        const error = new Error(code);
        error.searchCode = code;
        error.retryable = retryable !== false;
        return error;
    }

    function setupTitleSearch(options) {
        const settings = options || {};
        const targetDocument = settings.document || (defaultWindow && defaultWindow.document);
        const targetWindow = settings.window || defaultWindow;
        const request = settings.fetch || (targetWindow && targetWindow.fetch && targetWindow.fetch.bind(targetWindow));
        const AbortControllerType = settings.AbortController || (targetWindow && targetWindow.AbortController);
        const schedule = settings.setTimeout || (targetWindow && targetWindow.setTimeout.bind(targetWindow));
        const cancelScheduled = settings.clearTimeout || (targetWindow && targetWindow.clearTimeout.bind(targetWindow));
        if (!targetDocument || !request || !AbortControllerType || !schedule || !cancelScheduled) {
            return null;
        }

        const input = targetDocument.getElementById("title");
        const feedback = targetDocument.getElementById("title-search-feedback");
        const results = targetDocument.getElementById("title-search-results");
        if (!input || !feedback || !results) {
            return null;
        }

        let timer = null;
        let controller = null;
        let searchSequence = 0;

        function setFeedback(message, state, hidden) {
            feedback.textContent = message;
            feedback.dataset.state = state;
            feedback.hidden = Boolean(hidden);
        }

        function clearResults() {
            results.replaceChildren();
            results.hidden = true;
        }

        function cancelCurrentWork() {
            if (timer !== null) {
                cancelScheduled(timer);
                timer = null;
            }
            if (controller) {
                controller.abort();
                controller = null;
            }
        }

        function selectResult(fullTitle) {
            searchSequence += 1;
            cancelCurrentWork();
            input.value = fullTitle;
            clearResults();
            setFeedback("TMDB match selected.", "selected", false);
        }

        function renderSuggestion(result) {
            const suggestion = targetDocument.createElement("button");
            suggestion.type = "button";
            suggestion.className = "search-suggestion";
            suggestion.textContent = `Use “${result.full_title}”`;
            suggestion.addEventListener("click", function () {
                selectResult(result.full_title);
            });
            results.appendChild(suggestion);
            results.hidden = false;
        }

        function renderFailure(query, code, retryable) {
            const normalizedCode = normalizeErrorCode(code);
            clearResults();
            setFeedback(ERROR_MESSAGES[normalizedCode], `error-${normalizedCode}`, false);
            if (!retryable) {
                return;
            }
            const retry = targetDocument.createElement("button");
            retry.type = "button";
            retry.className = "search-suggestion search-retry";
            retry.textContent = "Retry search";
            retry.addEventListener("click", function () {
                if (input.value.trim() === query) {
                    startSearch(query, true);
                }
            });
            results.appendChild(retry);
            results.hidden = false;
        }

        async function runSearch(query, requestSequence) {
            const activeController = new AbortControllerType();
            controller = activeController;
            try {
                const response = await request(`/search?q=${encodeURIComponent(query)}`, {
                    signal: activeController.signal
                });
                let payload;
                try {
                    payload = await response.json();
                } catch (error) {
                    throw searchError("malformed_response", true);
                }
                if (requestSequence !== searchSequence) {
                    return;
                }
                if (!payload || typeof payload !== "object") {
                    throw searchError("malformed_response", true);
                }
                if (!response.ok || payload.error) {
                    throw searchError(
                        normalizeErrorCode(payload.error_code, response.status),
                        payload.retryable
                    );
                }
                if (!("result" in payload)) {
                    throw searchError("malformed_response", true);
                }
                if (!payload.result) {
                    clearResults();
                    setFeedback(
                        "No TMDB match found. You can save this title manually.",
                        "empty",
                        false
                    );
                    return;
                }
                const fullTitle = payload.result.full_title;
                if (typeof fullTitle !== "string" || !fullTitle.trim() || fullTitle.length > 200) {
                    throw searchError("malformed_response", true);
                }
                clearResults();
                setFeedback("TMDB match found. Review it or save manually.", "success", false);
                renderSuggestion({ full_title: fullTitle });
            } catch (error) {
                if (
                    requestSequence !== searchSequence ||
                    error.name === "AbortError" ||
                    activeController.signal.aborted
                ) {
                    return;
                }
                const code = error.searchCode || (error.name === "TypeError" ? "offline" : "provider_unavailable");
                renderFailure(query, code, error.retryable !== false);
            } finally {
                if (controller === activeController) {
                    controller = null;
                }
            }
        }

        function startSearch(query, retrying) {
            const requestSequence = ++searchSequence;
            cancelCurrentWork();
            clearResults();
            if (query.length < 2) {
                setFeedback("", "idle", true);
                return;
            }
            setFeedback(
                retrying ? "Retrying TMDB search..." : "Checking TMDB match...",
                retrying ? "retrying" : "pending",
                false
            );
            timer = schedule(function () {
                timer = null;
                void runSearch(query, requestSequence);
            }, retrying ? 0 : SEARCH_DEBOUNCE_MS);
        }

        function handleInput() {
            startSearch(input.value.trim(), false);
        }

        input.addEventListener("input", handleInput);
        setFeedback("", "idle", true);

        return {
            destroy: function () {
                searchSequence += 1;
                cancelCurrentWork();
                input.removeEventListener("input", handleInput);
            }
        };
    }

    return {
        ERROR_MESSAGES: ERROR_MESSAGES,
        SEARCH_DEBOUNCE_MS: SEARCH_DEBOUNCE_MS,
        setupTitleSearch: setupTitleSearch
    };
}));
