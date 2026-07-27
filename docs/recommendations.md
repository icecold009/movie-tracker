# Recommendation evaluation

The recommender is a content-based binary-feature baseline. The intended
offline evaluation is a chronological holdout: train on earlier watchlist
entries, rank an external candidate pool, and measure `precision@k` against
later held-out entries using the `(tmdb_id, media_type)` identity.

`recommendations.evaluate_holdout()` implements the metric without making a
network request. The current production rows predate TMDB feature persistence,
and the repository has no historical holdout or candidate snapshot, so no
real precision value is claimed yet. A future evaluation must record its dated
dataset, candidate source, `k`, result, and limitations; synthetic fixtures are
for unit tests only.
