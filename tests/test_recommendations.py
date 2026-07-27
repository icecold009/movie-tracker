import pytest

from recommendations import (
    cosine_similarity,
    explain_recommendation,
    extract_features,
    filter_unseen_candidates,
    precision_at_k,
    normalize_genre_ids,
    normalize_media_type,
    rank_candidates,
)


def test_normalize_genre_ids_filters_invalid_values_and_sorts():
    assert normalize_genre_ids([28, "12", 28, 0, -1, "bad", True]) == (12, 28)


def test_normalize_media_type_accepts_tmdb_values_only():
    assert normalize_media_type(" TV ") == "tv"
    assert normalize_media_type("series") is None
    assert normalize_media_type(None) is None


def test_extract_features_is_deterministic_and_includes_media_type():
    item = {"genre_ids": [28, 12, 28], "tmdb_media_type": "movie"}

    assert extract_features(item) == frozenset({"genre:12", "genre:28", "media:movie"})


def test_cosine_similarity_handles_identical_partial_and_empty_vectors():
    assert cosine_similarity({"a", "b"}, {"a", "b"}) == 1.0
    assert cosine_similarity({"a", "b"}, {"b", "c", "d"}) == pytest.approx(1 / (6**0.5))
    assert cosine_similarity(set(), {"a"}) == 0.0


def test_rank_candidates_is_stable_for_equal_scores():
    profile = {"genre:28"}
    candidates = [
        {"title": "Zulu", "tmdb_id": 2, "genre_ids": [28]},
        {"title": "Alpha", "tmdb_id": 1, "genre_ids": [28]},
    ]

    assert [item["title"] for item in rank_candidates(profile, candidates)] == [
        "Alpha",
        "Zulu",
    ]


def test_filter_unseen_candidates_excludes_identity_and_normalized_title_matches():
    entries = [
        {"tmdb_id": 10, "tmdb_media_type": "movie", "title": "Known"},
        {"tmdb_id": None, "tmdb_media_type": None, "title": "Want To Watch"},
    ]
    candidates = [
        {"tmdb_id": 10, "media_type": "movie", "title": "Different Label"},
        {"tmdb_id": 11, "media_type": "movie", "title": "  want   to watch "},
        {"tmdb_id": 12, "media_type": "tv", "title": "New Title"},
    ]

    assert filter_unseen_candidates(candidates, entries) == [candidates[2]]


def test_build_recommendations_uses_provider_order_for_cold_start():
    from recommendations import build_recommendations

    candidates = [
        {"title": "Popular One", "tmdb_id": 1, "media_type": "movie", "genre_ids": []},
        {"title": "Popular Two", "tmdb_id": 2, "media_type": "movie", "genre_ids": []},
    ]

    results = build_recommendations([], candidates)

    assert [result["title"] for result in results] == ["Popular One", "Popular Two"]
    assert all("popular pick" in result["reason"] for result in results)


def test_precision_at_k_uses_fixed_denominator():
    assert precision_at_k([1, 2, 3], {2, 4}, k=3) == pytest.approx(1 / 3)


def test_precision_at_k_rejects_non_positive_k():
    with pytest.raises(ValueError):
        precision_at_k([], set(), k=0)


def test_explain_recommendation_uses_strongest_deterministic_watchlist_match():
    candidate = {"genre_ids": [28, 12], "media_type": "movie"}
    entries = [
        {"title": "Second", "genre_ids": [28]},
        {"title": "First", "genre_ids": [28, 12]},
    ]

    assert explain_recommendation(candidate, entries) == (
        "Recommended because it shares 2 genres with First."
    )


def test_explain_recommendation_has_safe_no_overlap_fallback():
    assert explain_recommendation({"genre_ids": [99]}, [{"title": "Known"}]) == (
        "Recommended as a content match from your watchlist."
    )
