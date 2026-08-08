# Development devlog

I built this project in several distinct passes rather than in one clean
straight line. This is a reconstruction from the full `git log --stat`,
grouped by the problem I was trying to solve at the time. The questions are
prompts for me to expand later; the `notes:` lines are my honest first pass.

## Phase 1 — A small watchlist prototype

**When:** 2026-03-31  
**Commits:** `1ab102b` through `b815786`

I started with the basic product: a Flask app, a PostgreSQL data layer, TMDB
lookups, an admin login, Jinja templates, CSS, and a Procfile/Gunicorn setup.
The first commits were mostly about getting a complete path from adding a title
to displaying it again.

Ask yourself:

- What was hard here?
- What did I try that did not work?
- What did I learn?

notes: I got a working CRUD prototype quickly, but I had almost no evidence
beyond “it runs locally.” I was designing around a traditional Procfile-based
deployment before I had settled where the app would actually run. The early
admin login and database code were also largely untested, which made later
deployment and security work harder than it needed to be.

## Phase 2 — Moving to Vercel and discovering production problems

**When:** 2026-06-18 to 2026-07-26  
**Commits:** `6044775`, `43174c6`, `ef8e2ce`, `ac5f763`, `35e2010`, `a10845e`,
`6943e17`, `05bb9a2`, `80ddfee`, `86515a1`, `62162b5`

I moved the entrypoint from `app.py` to `api/index.py`, added the Vercel
configuration, removed the stale Render Procfile, added `/healthz`, and began
keeping a backlog and repository guidance. I also added tracked database
migrations instead of relying on the application to create its own schema.

Ask yourself:

- What was hard here?
- What did I try that did not work?
- What did I learn?

notes: My first production assumptions were wrong. A deployment could exist
while `/` returned 500 and `/healthz` returned 404, and the Supabase pooler
rejected a guessed tenant/username identity. I learned that deployment status
is not route health, and that the exact provider connection string matters more
than a plausible-looking one. I also learned that schema setup needs to be
explicit and reproducible instead of hidden inside application startup.

## Phase 3 — Making configuration, database work, and TMDB failures safer

**When:** 2026-07-26  
**Commits:** `4f90495`, `8ec912c`, `6256a95`, `182577a`, `470bea6`, `f690233`,
`3c2ec8c`, `dbe3937`, `c7f6d16`, `1096d90`, `46f63a2`, `ac28b89`

I hardened the runtime configuration, removed weak defaults and the obsolete
`init_db()` bootstrap, added database transaction cleanup and connection
timeouts, validated form input, and made database and TMDB failures safe for
users. TMDB searches gained response validation, caching, and a per-warm-
instance rate limit.

Ask yourself:

- What was hard here?
- What did I try that did not work?
- What did I learn?

notes: I initially tried to make the app forgiving with fallback configuration
and automatic schema setup. That made the boundary between development and
production less clear and could have allowed an unsafe deployment, so I
replaced it with fail-fast configuration and tracked migrations. The hardest
part was not one clever function; it was making every failure path—bad form
data, unavailable PostgreSQL, malformed TMDB responses, and slow connections—
fail without leaking implementation details. I also had to accept that the
TMDB protection is local to a warm serverless instance, not a global quota
system.

## Phase 4 — Adding recommendations without pretending I had an ML dataset

**When:** 2026-07-26 to 2026-07-27  
**Commits:** `ac28b89` and the recommendation work merged through PR #3

I added stored TMDB IDs, media types, and genre IDs, then built a deterministic
content-based recommender. It filters out titles already on the watchlist,
uses cosine similarity over simple feature tokens, produces explanations, and
falls back to popular picks when the watchlist profile is sparse. I also added
the `/recommendations` route and a small holdout/precision utility for future
evaluation.

Ask yourself:

- What was hard here?
- What did I try that did not work?
- What did I learn?

notes: I wanted one non-trivial feature, but I did not have enough watch history
to support a serious model or a trustworthy production metric. I chose a simple
baseline that I could explain and test instead of inventing a benchmark. The
holdout helper gives me a way to evaluate later, but it is not evidence that
the current recommendations are good. The lesson was to make the limitation
part of the product design rather than hide it behind the word “AI.”

## Phase 5 — Repairing tests, CI, and the difference between evidence types

**When:** 2026-07-27  
**Commits:** `0adbfec`, `c16ffa7`, `3c04a42`, `ef97ff9`, `c804c8e`, `8139c17`,
`9603b11`, `591fb18`, `4ef1e5f`, `6b2f4bb`, `e96b7f4`

I added the CI workflow, fixed test syntax and mocks, recorded database failure
behavior, documented privacy boundaries, and built a release checklist around
local tests, remote CI, live route probes, and reversible production writes.
The final local suite reached 47 tests, and the production record included
public routes, authorization rejection, and a temporary add/delete fixture.

Ask yourself:

- What was hard here?
- What did I try that did not work?
- What did I learn?

notes: I did break the verification path while iterating: test syntax and mock
assumptions had to be repaired before the checks were meaningful. Earlier
production probes also failed because the database connection was wrong, so I
could not treat a successful build as a successful deployment. I learned to
separate local test results, CI results, live HTTP checks, and browser evidence
instead of collapsing them into one “ready” label. I also learned that aggregate
usage events are activity counts, not user counts.

## Phase 6 — Making the interface feel deliberate and checking accessibility

**When:** 2026-07-27  
**Commits:** `24703c8`, `31bd0b0`, `956e590`, `c2d8fd5`, `5aac30a`, `2f10426`,
`500f0bf`

I added progressive loading skeletons, rebuilt the visual system, personalized
the hero, polished login and section headings, added the footer, and made
ratings more prominent. I then added explicit dialog state, focus trapping,
focus return, live announcements, and focused accessibility tests.

Ask yourself:

- What was hard here?
- What did I try that did not work?
- What did I learn?

notes: I spent a lot of time making the app look finished, and that work could
easily have become decoration without corresponding behavior. The loading and
rating changes became more useful once they were tied to actual state and
tests. I still do not have a proper browser surface for keyboard, screen-reader,
and responsive visual review, so the automated accessibility checks are useful
but incomplete. The lesson was that UI polish needs both interaction evidence
and an admission of what I could not manually verify.

## Phase 7 — Release consolidation and correcting the project story

**When:** 2026-07-27 to 2026-08-08  
**Commits:** `dfd8a96` and `8d489cc`

I consolidated the release-readiness work into the merged mainline commit and
then rewrote the README in first person. The README now explains why I built
the app, what was difficult, what is still limited, and what I would do
differently. This devlog is the missing companion: it records the path rather
than only describing the final state.

Ask yourself:

- What was hard here?
- What did I try that did not work?
- What did I learn?

notes: The release documentation became too much like an audit written by an
outside observer. Phrases such as “not currently claimed,” stale PR references,
and repeated verification summaries made the project sound more polished and
less personal than the commit history actually was. Rewriting the README fixed
the voice, but it could not by itself show the false starts. I learned that a
credible project needs both a clean final explanation and a record of the
decisions, failures, and evidence gaps that produced it.
