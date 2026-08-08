# Recommender evaluation design

## Decision

I am choosing an offline recommender evaluation as the first step toward a
properly measured recommender. This is not an online A/B test yet. It creates a
deterministic, synthetic watchlist from real TMDB metadata, evaluates the
existing content-based recommender on a chronological holdout, and writes a
dated report with the exact data counts and `precision@k` values.

The result will be useful evidence about whether this baseline can recover
held-out items from similar metadata. It will not prove that real users prefer
the recommendations, because the watchlist and holdout are synthetic.

## Goals

- Fetch enough real movie and TV metadata from TMDB to build a 200-entry local
  evaluation watchlist.
- Keep the run reproducible with a seed, recorded request parameters, and a
  local JSON snapshot/report.
- Use a chronological split: 160 earlier entries for training and 40 later
  entries as held-out positives.
- Evaluate against an explicit candidate pool containing the 40 held-out
  positives plus unseen negative candidates from TMDB. The candidate pool must
  be larger than the held-out set; otherwise precision would be misleadingly
  easy.
- Report `precision@1`, `precision@5`, and `precision@10`, plus the split sizes,
  candidate-pool composition, data date, and limitations.
- Keep the evaluation read-only with respect to the production database.

## Non-goals

- I am not adding Supabase tables, changing RLS, or seeding production data.
- I am not claiming that synthetic holdout precision is a user-satisfaction
  metric.
- I am not introducing a second recommender algorithm in this change.
- I am not implementing online A/B assignment, exposure logging, click/rating
  attribution, or statistical significance testing. Those need real users and
  a separate product decision.

## Proposed flow

1. Load `TMDB_API_KEY` from the existing ignored `.env` configuration. Never
   write the key to the output.
2. Fetch paginated `/discover/movie` and `/discover/tv` results from TMDB with
   `include_adult=false` and popularity ordering. Normalize both result shapes
   into the record format already used by `recommendations.py`:
   `title`, `tmdb_id`, `media_type`, `genre_ids`, and `release_date`.
3. Deduplicate by `(tmdb_id, media_type)`, discard records without an ID,
   title, media type, or release date, and retain enough records for both the
   watchlist and negative candidate pool.
4. Use a seeded, popularity-weighted selection with a light genre/media-type
   diversity constraint to choose 200 watchlist entries. The selection is
   synthetic, but every selected title and genre comes from TMDB.
5. Sort the selected watchlist by release date and use the first 160 records as
   training data and the latest 40 as the holdout. The ordering simulates the
   recommender seeing older watch history before newer titles arrive.
6. Build the candidate pool from all 40 held-out entries plus a seeded sample
   of 360 records that are not in the synthetic watchlist. These are evaluation
   negatives, not verified dislikes; the report must call them negatives only
   in the benchmark sense.
7. Run `recommendations.evaluate_holdout()` for `k=1`, `5`, and `10`. Fix the
   evaluator so it accepts either `media_type` or `tmdb_media_type` when
   constructing the identity key.
8. Write a report containing the retrieval date, seed, endpoint/page settings,
   watchlist/train/holdout/candidate counts, the metric values, and warnings.
   Optionally write the normalized snapshot so the exact run can be inspected
   without making another TMDB request.

## Proposed files

- `scripts/evaluate_recommender.py`: CLI, TMDB pagination, deterministic
  selection/split, report writing, and human-readable output.
- `tests/test_recommender_evaluation.py`: mocked TMDB payloads and tests for
  deduplication, deterministic selection, chronological split, candidate
  construction, and missing-field failures.
- `recommendations.py`: small identity-key fix in `evaluate_holdout()`.
- `docs/recommendations.md`: explain the synthetic benchmark and how to run it
  without presenting the result as production quality.
- `README.md`: only after a real run succeeds, add the dated result with the
  data size and caveat that this is a synthetic offline evaluation.

## What is hard about it

The metric itself is short; the hard part is making the benchmark honest.

- A random split can leak the same popularity/genre era into both sides. A
  chronological split is more realistic, but it is sensitive to the available
  release-date distribution.
- TMDB's popular pages are not a neutral catalog. They overrepresent visible
  and recent titles, so the benchmark will not represent every kind of movie or
  show.
- A candidate that is not selected into the synthetic watchlist is not truly a
  negative preference. It is only an unseen candidate for this experiment.
- The current recommender uses a union of all training features, not per-item
  preference weights. A high precision result could still hide a weak model.
- `precision@k` has a fixed denominator. When fewer than `k` recommendations
  are available, the score correctly falls, but the report must show the actual
  recommendation count as context.
- Real TMDB data changes. The snapshot, seed, date, page count, and exact result
  counts are therefore part of the result, not optional metadata.

## What could go wrong

- The API key may be missing, invalid, rate-limited, or unavailable from the
  current network.
- TMDB may return fewer unique records than requested or omit dates/genres.
- Pagination may produce duplicates or mixed movie/TV shapes that are handled
  incorrectly.
- A deterministic selector may accidentally over-sample one genre or media
  type and make the result look better than it is.
- The holdout may contain no items that overlap the learned genre profile, which
  would produce a legitimate but uninformative zero.
- The candidate negatives may be too easy or too similar to the positives.
- Someone may copy the number into the README later without preserving the
  date, split, candidate pool, or synthetic-data caveat.

The script should fail loudly when it cannot meet the requested counts. It
should not silently shrink the benchmark and still print a flattering number.

## What I need to learn

I already understand the current feature extraction, ranking, filtering, and
fixed-denominator precision function. I still need to learn enough about:

- Designing temporal offline evaluation without leakage.
- Choosing and documenting negative candidates when explicit negative labels do
  not exist.
- Interpreting precision variance for one synthetic split and deciding when a
  confidence interval or repeated splits is warranted.
- TMDB pagination, rate limits, attribution, and acceptable local caching for an
  evaluation snapshot.
- The statistical and product requirements for a future online A/B test:
  stable assignment, exposure logging, outcome definitions, guardrails, and
  minimum sample size.

## Verification plan

Before using any number in the README, I will:

1. Run the unit tests with mocked TMDB responses.
2. Run the script against real TMDB data with an explicit seed.
3. Inspect the output counts and a small sample of records.
4. Confirm that the held-out identities are absent from training and that the
   candidate pool contains both positives and negatives.
5. Record the exact command, date, seed, result, and limitations in the report
   and documentation.

The final claim will be phrased as an offline synthetic benchmark result, not
as proof of recommendation quality for real users.
