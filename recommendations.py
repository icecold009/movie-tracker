"""Small, deterministic primitives for explainable recommendations."""

import math


VALID_MEDIA_TYPES = frozenset({"movie", "tv"})


def _read(item, key, default=None):
    """Read a field from a recommendation record without hiding bad records."""
    if isinstance(item, dict):
        return item.get(key, default)
    return default


def normalize_title(value):
    """Collapse whitespace and normalize case for title comparisons."""
    return " ".join(str(value or "").split()).casefold()


def normalize_genre_ids(values):
    """Return unique, positive TMDB genre IDs in stable order."""
    if values is None or isinstance(values, (str, bytes)):
        return ()

    try:
        iterator = iter(values)
    except TypeError:
        return ()

    genre_ids = set()
    for value in iterator:
        if isinstance(value, bool):
            continue
        try:
            genre_id = int(value)
        except (TypeError, ValueError):
            continue
        if genre_id > 0:
            genre_ids.add(genre_id)
    return tuple(sorted(genre_ids))


def normalize_media_type(value):
    """Normalize supported TMDB media types and reject everything else."""
    if not isinstance(value, str):
        return None
    media_type = value.strip().casefold()
    if media_type not in VALID_MEDIA_TYPES:
        return None
    return media_type


def _item_media_type(item):
    """Resolve the current and legacy media-type field names."""
    raw_media_type = _read(item, "tmdb_media_type") or _read(item, "media_type")
    return normalize_media_type(raw_media_type)


def extract_features(item):
    """Convert one record into binary genre and media-type feature tokens."""
    features = {f"genre:{genre_id}" for genre_id in normalize_genre_ids(_read(item, "genre_ids"))}
    media_type = _item_media_type(item)
    if media_type:
        features.add(f"media:{media_type}")
    return frozenset(features)


def cosine_similarity(left_features, right_features):
    """Calculate cosine similarity for binary feature-token vectors."""
    left = set(left_features)
    right = set(right_features)
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / math.sqrt(len(left) * len(right))


def _candidate_sort_key(candidate, score):
    tmdb_id = _read(candidate, "tmdb_id")
    stable_id = tmdb_id if isinstance(tmdb_id, int) and not isinstance(tmdb_id, bool) else 0
    return (-score, normalize_title(_read(candidate, "title")), stable_id)


def rank_candidates(profile_features, candidates):
    """Return candidates ordered by score, title, and TMDB ID."""
    scored = []
    for candidate in candidates:
        score = cosine_similarity(profile_features, extract_features(candidate))
        scored.append((score, candidate))

    scored.sort(key=lambda item: _candidate_sort_key(item[1], item[0]))
    return [candidate for _, candidate in scored]


def _record_identity(item):
    """Return a usable TMDB identity, or ``None`` for incomplete records."""
    tmdb_id = _read(item, "tmdb_id")
    media_type = _item_media_type(item)
    if not isinstance(tmdb_id, int) or isinstance(tmdb_id, bool) or not media_type:
        return None
    return tmdb_id, media_type


def filter_unseen_candidates(candidates, entries):
    """Exclude records already present by identity or normalized title."""
    seen_ids = set()
    seen_titles = set()
    for entry in entries:
        identity = _record_identity(entry)
        if identity is not None:
            seen_ids.add(identity)
        title = normalize_title(_read(entry, "title"))
        if title:
            seen_titles.add(title)

    unseen = []
    for candidate in candidates:
        if _record_identity(candidate) in seen_ids:
            continue
        if normalize_title(_read(candidate, "title")) in seen_titles:
            continue
        unseen.append(candidate)
    return unseen


def _genre_features(item):
    return {token for token in extract_features(item) if token.startswith("genre:")}


def explain_recommendation(candidate, source_entries):
    """Explain the strongest genre overlap behind a recommendation."""
    candidate_genres = _genre_features(candidate)
    matches = []
    for entry in source_entries:
        shared_count = len(candidate_genres.intersection(_genre_features(entry)))
        if shared_count:
            matches.append(
                (
                    -shared_count,
                    normalize_title(_read(entry, "title")),
                    _read(entry, "title") or "your watchlist",
                    shared_count,
                )
            )

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

    recommendations = []
    for candidate in rank_candidates(profile_features, unseen):
        if cosine_similarity(profile_features, extract_features(candidate)) <= 0:
            continue
        recommendation = dict(candidate)
        recommendation["reason"] = explain_recommendation(candidate, source_entries)
        recommendation["reason_tags"] = reason_tags(candidate, source_entries)
        recommendations.append(recommendation)
    return recommendations[:limit]


def precision_at_k(recommended_ids, relevant_ids, k=10):
    """Return binary precision@k with a fixed denominator of ``k``."""
    if k <= 0:
        raise ValueError("k must be positive")
    recommended = list(recommended_ids)[:k]
    return len(set(recommended).intersection(set(relevant_ids))) / k


def evaluate_holdout(training_entries, heldout_entries, candidate_pool, k=10):
    """Evaluate recommendations against a held-out set without network access."""
    recommendations = build_recommendations(training_entries, candidate_pool, limit=k)
    recommended_ids = [(_read(item, "tmdb_id"), _item_media_type(item)) for item in recommendations]
    relevant_ids = {
        (_read(item, "tmdb_id"), _item_media_type(item))
        for item in heldout_entries
    }
    return {
        "k": k,
        "recommendation_count": len(recommendations),
        "precision_at_k": precision_at_k(recommended_ids, relevant_ids, k),
    }
