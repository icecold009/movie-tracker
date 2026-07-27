# Recommendation evaluation

The recommender is a content-based binary-feature baseline. The intended
offline evaluation is a chronological holdout: train on earlier watchlist
entries, rank an external candidate pool, and measure `precision@k` against
later held-out entries using the `(tmdb_id, media_type)` identity.

`recommendations.evaluate_holdout()` implements the metric without making a
network request. A read-only production metadata recheck on 2026-07-27 found
10 total entries, all watched, but only 1 watched entry with both `tmdb_id` and
`genre_ids`. That is still insufficient for a meaningful chronological
holdout, so no real precision value is claimed. A future evaluation must record
its dated dataset, candidate source, `k`, result, and limitations; synthetic
fixtures are for unit tests only.
