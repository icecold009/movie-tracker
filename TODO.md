# Final Luna plan — Movie Tracker

Repository: `C:\Users\91829\OneDrive\Documents\GitHub\movie-tracker`
Reviewed: clean `main` at `a78867d` on 2026-08-25
Feature branch: `codex/luna-movie-browser-recovery`

Tracker ownership: `BACKLOG.md` remains the working source of truth. Select work and record completion evidence there while using this file as Luna's sequenced execution contract.

## Current verified baseline

- `node --check static/app.js` passed.
- Pytest: 67 tests passed on the repository virtual environment.
- Search now uses AbortController plus a sequence guard; required production configuration already fails closed.
- Metadata trust states and privacy-sensitive public README boundaries are already implemented. Extend, do not duplicate.

## Code-review conclusion

The rapid-search overwrite bug is fixed, but search still collapses timeout, malformed JSON, rate limit, offline, and provider failures into one message and has no JavaScript/browser test harness. Current code also clears useful prior results immediately. The next branch should turn those states into verified behavior and then close browser/session/data-lifecycle gates.

## Build checklist

- [ ] **1. Add a small frontend test harness**
  Files: `package.json` or equivalent tooling, `static/app.js`, new DOM tests.
  What to build: Add reproducible JavaScript unit/DOM tests without changing the Flask deployment contract.
  Acceptance: A clean checkout can run syntax plus frontend tests with a locked dependency set.
  Verify: Tests for debounce, abort, sequence ordering, clear input, no result, and suggestion selection.

- [ ] **2. Model distinct search failure states**
  Files: `static/app.js`, templates/status markup, `/search` contract tests.
  What to build: Add bounded timeout, safe non-JSON parsing, and distinct offline, rate-limited, provider-unavailable, malformed, and retry states. Decide deliberately whether last good results remain visible while pending.
  Acceptance: Old responses never apply, user input is preserved, and each state has an honest next action.
  Verify: Reordered-response DOM tests and Flask route tests for every status/code.

- [ ] **3. Add end-to-end form and modal recovery**
  Files: Playwright/browser tests and focused UI fixes.
  What to build: Cover add/edit/delete, focus trap/Escape/return, CSRF failure, duplicate, session expiry, database failure, metadata fallback, and reload.
  Acceptance: Form values survive retryable failures; destructive actions are explicit; 320px/200% zoom does not hide errors or controls.
  Verify: Keyboard-only browser suite with forced error responses.

- [ ] **4. Complete recommendation and metadata trust UI**
  Files: templates, metadata state helpers, recommender explanations.
  What to build: Show source, freshness, stale/manual/missing state, sparse-input limitations, and correction path consistently across cards, detail, and edit.
  Acceptance: Cached/fallback data and recommendation uncertainty are human-readable and never presented as exact model certainty.
  Verify: Existing metadata/recommendation tests plus browser assertions.

- [ ] **5. Define private data lifecycle**
  Files: backend routes, migration/docs as needed, private runbook.
  What to build: Specify export, delete, retention, logs, analytics, screenshots, and session-expiry behavior for watch history, ratings, notes, and recommendations.
  Acceptance: Authorization and CSRF cover every mutation; exports/deletes do not cross accounts or leak configuration.
  Verify: Extend authorization/mutation tests and inspect logs/error bodies.

- [ ] **6. Run production evidence gates privately**
  Files: private evidence notes; public README stays sanitized.
  What to build: Verify the intended Vercel/Supabase/TMDB path, migration state, session recovery, slow/offline behavior, and pooler identity without publishing identifiers or metrics.
  Acceptance: Production, provider, database, browser, and local results are recorded separately.
  Verify: `node --check static/app.js`; `python -m pytest`; frontend/browser tests; `git diff --check`.

## Commit checkpoints

1. `test(search): add request-order and failure-state coverage`
2. `feat(movie): finish browser and session recovery`
3. `docs(movie): define private data and production gates`

## Definition of done

- [ ] Search races and all expected failures have automated coverage.
- [ ] Forms/modals preserve work and focus across failures.
- [ ] Recommendation and metadata evidence is truthful and correctable.
- [ ] Sensitive production evidence remains private and clearly separated.
- [ ] Feature branch is pushed and clean; `main` is untouched and unmerged.

