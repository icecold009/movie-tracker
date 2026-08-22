"""Deterministic primitives for explainable content recommendations."""

import math


VALID_MEDIA_TYPES = {"movie", "tv"}


def normalize_title(value):
    return " ".join(str(value or "").split()).casefold()


def normalize_genre_ids(values):
    """Return sorted, unique positive TMDB genre IDs."""
    if values is None or isinstance(values, (str, bytes)):
        return ()

    normalized = set()
    for value in values:
        if isinstance(value, bool):
            continue
        try:
            genre_id = int(value)
        except (TypeError, ValueError):
            continue
        if genre_id > 0:
            normalized.add(genre_id)
    return tuple(sorted(normalized))


def normalize_media_type(value):
    """Normalize TMDB media types while rejecting unsupported values."""
    if not isinstance(value, str):
        return None
    media_type = value.strip().casefold()
    return media_type if media_type in VALID_MEDIA_TYPES else None


def extract_features(item):
    """Return binary feature tokens for a watchlist or candidate record."""
    features = {f"genre:{genre_id}" for genre_id in normalize_genre_ids(item.get("genre_ids"))}
    media_type = normalize_media_type(item.get("tmdb_media_type") or item.get("media_type"))
    if media_type:
        features.add(f"media:{media_type}")
    return frozenset(features)


def cosine_similarity(left_features, right_features):
    """Calculate cosine similarity for binary feature-token vectors."""
    left = set(left_features)
    right = set(right_features)
    if not left or not right:
        return 0.0
    return len(left & right) / math.sqrt(len(left) * len(right))


def rank_candidates(profile_features, candidates):
    """Rank candidates by score, then title and TMDB ID for stable output."""
    ranked = []
    for candidate in candidates:
        features = extract_features(candidate)
        score = cosine_similarity(profile_features, features)
        title = str(candidate.get("title", "")).casefold()
        tmdb_id = candidate.get("tmdb_id")
        ranked.append((score, title, tmdb_id if isinstance(tmdb_id, int) else 0, candidate))

    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [candidate for _, _, _, candidate in ranked]


def filter_unseen_candidates(candidates, entries):
    """Exclude titles already on the watchlist using identity or title."""
    seen_ids = set()
    seen_titles = set()
    for entry in entries:
        tmdb_id = entry.get("tmdb_id")
        media_type = normalize_media_type(entry.get("tmdb_media_type"))
        if isinstance(tmdb_id, int) and not isinstance(tmdb_id, bool) and media_type:
            seen_ids.add((tmdb_id, media_type))
        title = normalize_title(entry.get("title"))
        if title:
            seen_titles.add(title)

    unseen = []
    for candidate in candidates:
        candidate_id = candidate.get("tmdb_id")
        candidate_media_type = normalize_media_type(
            candidate.get("tmdb_media_type") or candidate.get("media_type")
        )
        identity = (candidate_id, candidate_media_type)
        if identity in seen_ids or normalize_title(candidate.get("title")) in seen_titles:
            continue
        unseen.append(candidate)
    return unseen


def explain_recommendation(candidate, source_entries):
    """Explain the strongest watchlist overlap behind a recommendation."""
    candidate_genres = {
        token for token in extract_features(candidate) if token.startswith("genre:")
    }
    matches = []
    for entry in source_entries:
        entry_genres = {
            token for token in extract_features(entry) if token.startswith("genre:")
        }
        shared_count = len(candidate_genres & entry_genres)
        if shared_count:
            matches.append((
                -shared_count,
                normalize_title(entry.get("title")),
                entry.get("title") or "your watchlist",
                shared_count,
            ))

    if not matches:
        return "Recommended as a content match from your watchlist."

    _, _, source_title, shared_count = min(matches)
    noun = "genre" if shared_count == 1 else "genres"
    return f"Recommended because it shares {shared_count} {noun} with {source_title}."


def reason_tags(candidate, source_entries):
    """Return restrained labels describing the evidence behind a result."""
    candidate_genres = {
        token for token in extract_features(candidate) if token.startswith("genre:")
    }
    has_genre_overlap = any(
        candidate_genres & {
            token for token in extract_features(entry) if token.startswith("genre:")
        }
        for entry in source_entries
    )
    if has_genre_overlap:
        return ["Genre affinity", "Watch history"]
    if source_entries:
        return ["Discovery signal"]
    return ["Discovery signal", "Fallback path"]


def build_recommendations(entries, candidates, limit=10):
    """Build scored, unseen, explained recommendations from feature data."""
    source_entries = [entry for entry in entries if extract_features(entry)]
    profile_features = set()
    for entry in source_entries:
        profile_features.update(extract_features(entry))

    unseen = filter_unseen_candidates(candidates, entries)
    if not profile_features:
        return [
            {
                **candidate,
                "reason": "Recommended as a popular pick while your watchlist profile is still sparse.",
                "reason_tags": ["Discovery signal", "Fallback path"],
            }
            for candidate in unseen[:limit]
        ]

    ranked = rank_candidates(profile_features, unseen)
    recommendations = []
    for candidate in ranked:
        if cosine_similarity(profile_features, extract_features(candidate)) <= 0:
            continue
        recommendation = dict(candidate)
        recommendation["reason"] = explain_recommendation(candidate, source_entries)
        recommendation["reason_tags"] = reason_tags(candidate, source_entries)
        recommendations.append(recommendation)
    return recommendations[:limit]


def precision_at_k(recommended_ids, relevant_ids, k=10):
    """Return binary precision@k with a fixed denominator of k."""
    if k <= 0:
        raise ValueError("k must be positive")
    recommended = list(recommended_ids)[:k]
    relevant = set(relevant_ids)
    return len(set(recommended) & relevant) / k


def evaluate_holdout(training_entries, heldout_entries, candidate_pool, k=10):
    """Evaluate a recommendation holdout without fetching external data."""
    recommendations = build_recommendations(training_entries, candidate_pool, limit=k)
    recommended_ids = [
        (item.get("tmdb_id"), normalize_media_type(item.get("media_type")))
        for item in recommendations
    ]
    relevant_ids = {
        (
            item.get("tmdb_id"),
            normalize_media_type(
                item.get("tmdb_media_type") or item.get("media_type")
            ),
        )
        for item in heldout_entries
    }
    return {
        "k": k,
        "recommendation_count": len(recommendations),
        "precision_at_k": precision_at_k(recommended_ids, relevant_ids, k),
    }
