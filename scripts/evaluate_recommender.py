"""Run a reproducible synthetic holdout evaluation using TMDB metadata."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# Allow both `python -m scripts.evaluate_recommender` and
# `python scripts/evaluate_recommender.py` from the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from recommendations import (
    evaluate_holdout,
    normalize_genre_ids,
    normalize_media_type,
    normalize_title,
)


TMDB_DISCOVER_URL = "https://api.themoviedb.org/3/discover"
MEDIA_TYPES = ("movie", "tv")
DEFAULT_WATCHLIST_SIZE = 200
DEFAULT_HOLDOUT_SIZE = 40
DEFAULT_NEGATIVE_COUNT = 360
DEFAULT_PAGES_PER_MEDIA_TYPE = 15
DEFAULT_TIMEOUT_SECONDS = 10


class EvaluationError(RuntimeError):
    """Raised when the evaluation cannot produce the requested dataset."""


def _positive_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise EvaluationError(f"{name} must be a positive integer")
    return value


def _normalize_date(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def normalize_tmdb_result(result, media_type):
    """Convert one TMDB discover result into the local evaluation shape."""
    if not isinstance(result, dict):
        return None
    if media_type not in MEDIA_TYPES:
        raise EvaluationError(f"unsupported media type: {media_type}")

    tmdb_id = result.get("id")
    if isinstance(tmdb_id, bool) or not isinstance(tmdb_id, int) or tmdb_id <= 0:
        return None

    title = result.get("title") if media_type == "movie" else result.get("name")
    release_value = (
        result.get("release_date")
        if media_type == "movie"
        else result.get("first_air_date")
    )
    release_date = _normalize_date(release_value)
    genre_ids = normalize_genre_ids(result.get("genre_ids"))
    if not isinstance(title, str) or not title.strip() or not release_date or not genre_ids:
        return None

    popularity = result.get("popularity", 0.0)
    if isinstance(popularity, bool) or not isinstance(popularity, (int, float)):
        popularity = 0.0

    return {
        "title": " ".join(title.split()),
        "tmdb_id": tmdb_id,
        "media_type": media_type,
        "genre_ids": list(genre_ids),
        "release_date": release_date,
        "popularity": max(float(popularity), 0.0),
    }


def _request_page(session, api_key, media_type, page, timeout):
    try:
        response = session.get(
            f"{TMDB_DISCOVER_URL}/{media_type}",
            params={
                "api_key": api_key,
                "include_adult": "false",
                "sort_by": "popularity.desc",
                "page": page,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        raise EvaluationError(
            f"TMDB request failed for {media_type} page {page}: {type(error).__name__}"
        ) from error

    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise EvaluationError(f"TMDB returned an invalid {media_type} page shape")
    return payload


def fetch_catalog(
    api_key,
    pages_per_media_type=DEFAULT_PAGES_PER_MEDIA_TYPE,
    session=None,
    timeout=DEFAULT_TIMEOUT_SECONDS,
    request_delay=0.25,
):
    """Fetch and normalize a bounded TMDB catalog for the evaluation."""
    if not isinstance(api_key, str) or not api_key.strip():
        raise EvaluationError("TMDB_API_KEY is required")
    _positive_int(pages_per_media_type, "pages_per_media_type")
    session = session or requests.Session()

    records = {}
    pages_fetched = 0
    for media_type in MEDIA_TYPES:
        for page in range(1, pages_per_media_type + 1):
            payload = _request_page(session, api_key, media_type, page, timeout)
            pages_fetched += 1
            for result in payload["results"]:
                normalized = normalize_tmdb_result(result, media_type)
                if normalized:
                    key = (normalized["tmdb_id"], normalized["media_type"])
                    records[key] = normalized

            total_pages = payload.get("total_pages")
            if isinstance(total_pages, int) and page >= total_pages:
                break
            if request_delay:
                time.sleep(request_delay)

    return list(records.values()), pages_fetched


def _weighted_sample(records, count, rng):
    """Sample without replacement using popularity and genre novelty."""
    if count > len(records):
        raise EvaluationError(
            f"requested {count} records but only {len(records)} are available"
        )

    pool = list(records)
    selected = []
    seen_genres = set()
    while len(selected) < count:
        weights = []
        for record in pool:
            novelty = len(set(record["genre_ids"]) - seen_genres)
            popularity_weight = max(math.sqrt(record.get("popularity", 0.0)), 0.1)
            weights.append(popularity_weight * (1 + 0.15 * novelty))
        chosen = rng.choices(pool, weights=weights, k=1)[0]
        selected.append(chosen)
        seen_genres.update(chosen["genre_ids"])
        pool.remove(chosen)
    return selected


def select_watchlist(catalog, size=DEFAULT_WATCHLIST_SIZE, seed=20260808):
    """Select a deterministic, popularity-weighted and media-balanced sample."""
    _positive_int(size, "watchlist_size")
    if size % 2:
        raise EvaluationError("watchlist_size must be even for media balancing")
    rng = random.Random(seed)
    selected = []
    target_per_type = size // 2
    selected_titles = set()
    for media_type in MEDIA_TYPES:
        records = [
            item
            for item in catalog
            if item["media_type"] == media_type
            and normalize_title(item["title"]) not in selected_titles
        ]
        chosen = _weighted_sample(records, target_per_type, rng)
        selected.extend(chosen)
        selected_titles.update(normalize_title(item["title"]) for item in chosen)
    return sorted(selected, key=lambda item: (item["release_date"], item["tmdb_id"]))


def chronological_split(watchlist, holdout_size=DEFAULT_HOLDOUT_SIZE):
    """Return earlier training entries and later held-out entries."""
    _positive_int(holdout_size, "holdout_size")
    if len(watchlist) <= holdout_size:
        raise EvaluationError("watchlist must be larger than holdout_size")
    ordered = sorted(watchlist, key=lambda item: (item["release_date"], item["tmdb_id"]))
    return ordered[:-holdout_size], ordered[-holdout_size:]


def _identity(item):
    return item["tmdb_id"], normalize_media_type(item.get("media_type") or item.get("tmdb_media_type"))


def build_candidate_pool(
    catalog,
    watchlist,
    holdout,
    negative_count=DEFAULT_NEGATIVE_COUNT,
    seed=20260808,
):
    """Combine held-out positives with unseen benchmark negatives."""
    _positive_int(negative_count, "negative_count")
    watchlist_ids = {_identity(item) for item in watchlist}
    watchlist_titles = {normalize_title(item["title"]) for item in watchlist}
    negative_titles = set()
    negatives = []
    for item in catalog:
        title = normalize_title(item["title"])
        if (
            _identity(item) not in watchlist_ids
            and title not in watchlist_titles
            and title not in negative_titles
        ):
            negatives.append(item)
            negative_titles.add(title)
    rng = random.Random(seed + 1)
    sampled_negatives = _weighted_sample(negatives, negative_count, rng)
    pool = list(holdout) + sampled_negatives
    if len({_identity(item) for item in pool}) != len(pool):
        raise EvaluationError("candidate pool contains duplicate identities")
    return pool, len(sampled_negatives)


def evaluate_metrics(training, holdout, candidate_pool, ks=(1, 5, 10)):
    metrics = {}
    for k in ks:
        result = evaluate_holdout(training, holdout, candidate_pool, k=k)
        metrics[f"precision@{k}"] = {
            "value": result["precision_at_k"],
            "recommendation_count": result["recommendation_count"],
            "k": result["k"],
        }
    return metrics


def build_report(
    catalog,
    watchlist,
    training,
    holdout,
    candidate_pool,
    negative_count,
    pages_fetched,
    seed,
    pages_per_media_type,
    metrics,
):
    return {
        "evaluation": "synthetic_tmdb_chronological_holdout",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "tmdb": {
            "media_types": list(MEDIA_TYPES),
            "pages_per_media_type": pages_per_media_type,
            "pages_fetched": pages_fetched,
            "catalog_records": len(catalog),
        },
        "dataset": {
            "watchlist_records": len(watchlist),
            "training_records": len(training),
            "heldout_positive_records": len(holdout),
            "candidate_pool_records": len(candidate_pool),
            "candidate_pool_positive_records": len(holdout),
            "candidate_pool_benchmark_negative_records": negative_count,
            "split": "chronological by TMDB release/first-air date",
        },
        "metrics": metrics,
        "limitations": [
            "The watchlist and holdout are synthetic selections from TMDB metadata.",
            "Candidate negatives are unseen benchmark candidates, not verified dislikes.",
            "TMDB popularity pages overrepresent visible and recent titles.",
            "This offline result does not measure user satisfaction or online A/B lift.",
        ],
    }


def _write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_snapshot(catalog, watchlist, training, holdout, candidate_pool):
    return {
        "catalog": catalog,
        "watchlist": watchlist,
        "training": training,
        "holdout": holdout,
        "candidate_pool": candidate_pool,
    }


def run_evaluation(args):
    load_dotenv()
    api_key = os.getenv("TMDB_API_KEY", "").strip()
    catalog, pages_fetched = fetch_catalog(
        api_key,
        pages_per_media_type=args.pages_per_media_type,
        timeout=args.timeout,
        request_delay=args.request_delay,
    )
    watchlist = select_watchlist(catalog, args.watchlist_size, args.seed)
    training, holdout = chronological_split(watchlist, args.holdout_size)
    candidate_pool, negative_count = build_candidate_pool(
        catalog,
        watchlist,
        holdout,
        args.negative_count,
        args.seed,
    )
    metrics = evaluate_metrics(training, holdout, candidate_pool)
    report = build_report(
        catalog,
        watchlist,
        training,
        holdout,
        candidate_pool,
        negative_count,
        pages_fetched,
        args.seed,
        args.pages_per_media_type,
        metrics,
    )
    if args.output:
        _write_json(args.output, report)
    if args.snapshot:
        _write_json(
            args.snapshot,
            build_snapshot(catalog, watchlist, training, holdout, candidate_pool),
        )
    return report


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watchlist-size", type=int, default=DEFAULT_WATCHLIST_SIZE)
    parser.add_argument("--holdout-size", type=int, default=DEFAULT_HOLDOUT_SIZE)
    parser.add_argument("--negative-count", type=int, default=DEFAULT_NEGATIVE_COUNT)
    parser.add_argument("--pages-per-media-type", type=int, default=DEFAULT_PAGES_PER_MEDIA_TYPE)
    parser.add_argument("--seed", type=int, default=20260808)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--request-delay", type=float, default=0.25)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--snapshot", type=Path)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        report = run_evaluation(args)
    except EvaluationError as error:
        raise SystemExit(f"evaluation failed: {error}") from error
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
