# Recommendation evaluation

The recommender is a content-based binary-feature baseline. The offline
evaluation uses a chronological holdout: train on earlier watchlist entries,
rank an external candidate pool, and measure `precision@k` against later
held-out entries using the `(tmdb_id, media_type)` identity.

`recommendations.evaluate_holdout()` implements the metric without making a
network request. A read-only production metadata recheck on 2026-07-27 found
10 total entries, all watched, but only 1 watched entry with both `tmdb_id` and
`genre_ids`. That is still insufficient for a meaningful production holdout, so
no real user-quality precision value is claimed. A synthetic benchmark is not
production evidence, but it is still useful when the real watchlist is too
small to support a holdout. The benchmark below uses real TMDB metadata to
create a deterministic local dataset without writing to Supabase.

## Synthetic benchmark run

On **2026-08-08**, `scripts/evaluate_recommender.py` fetched 30 TMDB discovery
pages and normalized 585 records. With seed `20260808`, it selected a balanced
200-entry synthetic watchlist, used 160 earlier entries for training, and held
out the latest 40 entries by release/first-air date. The candidate pool had 400
records: 40 held-out positives and 360 unseen benchmark negatives.

| Metric | Result |
|---|---:|
| `precision@1` | `0.000` |
| `precision@5` | `0.000` |
| `precision@10` | `0.000` |

This is an honest baseline result, not a claim that real users dislike the
recommendations. The benchmark negatives are unseen titles, not verified
dislikes; TMDB popularity pages are biased toward visible/recent titles; and
the watchlist itself is synthetic. The result says that this simple feature
union did not recover any of the 40 held-out titles in the top 10 for this
split. I need real watch history and an online experiment before making a
product-quality claim.

To reproduce it with a local `TMDB_API_KEY`:

```bash
python scripts/evaluate_recommender.py \
  --seed 20260808 \
  --output work/recommender-evaluation.json \
  --snapshot work/recommender-evaluation-snapshot.json
```
