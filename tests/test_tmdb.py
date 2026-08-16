from unittest.mock import Mock

import pytest
import requests

import tmdb


@pytest.fixture(autouse=True)
def clear_tmdb_state():
    with tmdb._state_lock:
        tmdb._cache.clear()
        tmdb._request_times.clear()


def response_with(data, status_code=200):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = data
    response.raise_for_status.return_value = None
    return response


def test_search_success_filters_people_and_builds_poster_url(monkeypatch):
    response = response_with(
        {
            "results": [
                {"media_type": "person", "name": "Ignored Person"},
                {
                    "media_type": "movie",
                    "id": 123,
                    "title": "Example Movie",
                    "poster_path": "/example.jpg",
                    "genre_ids": [28, "invalid"],
                },
            ]
        }
    )
    request = Mock(return_value=response)
    monkeypatch.setattr(tmdb.requests, "get", request)

    result = tmdb.search_tmdb("Example")

    assert result == {
        "full_title": "Example Movie",
        "poster_url": "https://image.tmdb.org/t/p/w500/example.jpg",
        "media_type": "movie",
        "tmdb_id": 123,
        "genre_ids": [28],
    }
    request.assert_called_once()
    assert request.call_args.kwargs["timeout"] == tmdb.TMDB_REQUEST_TIMEOUT_SECONDS


def test_cache_evicts_expired_and_oldest_entries(monkeypatch):
    monkeypatch.setattr(tmdb, "TMDB_CACHE_MAX_ENTRIES", 2)

    tmdb._set_cached("old", "old", 0)
    tmdb._set_cached("fresh", "fresh", 1)
    tmdb._set_cached("new", "new", 2)

    assert set(tmdb._cache) == {"fresh", "new"}

    tmdb._set_cached("expired", "expired", tmdb.TMDB_CACHE_TTL_SECONDS + 3)
    assert set(tmdb._cache) == {"expired"}


def test_search_returns_none_for_no_usable_results(monkeypatch):
    monkeypatch.setattr(
        tmdb.requests,
        "get",
        Mock(return_value=response_with({"results": [{"media_type": "person"}]})),
    )

    assert tmdb.search_tmdb("No Title") is None


def test_search_wraps_timeout(monkeypatch):
    monkeypatch.setattr(
        tmdb.requests,
        "get",
        Mock(side_effect=requests.Timeout("timed out")),
    )

    with pytest.raises(tmdb.TMDBRequestError, match="too long"):
        tmdb.search_tmdb("Timeout")


def test_search_enforces_warm_instance_rate_limit(monkeypatch):
    response = response_with({"results": []})
    request = Mock(return_value=response)
    monkeypatch.setattr(tmdb.requests, "get", request)
    monkeypatch.setattr(tmdb.time, "monotonic", lambda: 100.0)

    for index in range(tmdb.TMDB_RATE_LIMIT_MAX_REQUESTS):
        assert tmdb.search_tmdb(f"Title {index}") is None

    with pytest.raises(tmdb.TMDBRateLimitError, match="rate limit"):
        tmdb.search_tmdb("Title over limit")

    assert request.call_count == tmdb.TMDB_RATE_LIMIT_MAX_REQUESTS


def test_search_wraps_non_success_status(monkeypatch):
    response = response_with({}, status_code=503)
    response.raise_for_status.side_effect = requests.HTTPError("503")
    monkeypatch.setattr(tmdb.requests, "get", Mock(return_value=response))

    with pytest.raises(tmdb.TMDBResponseError, match="returned an error"):
        tmdb.search_tmdb("Unavailable")


def test_search_wraps_provider_quota_status(monkeypatch):
    response = response_with({}, status_code=429)
    response.raise_for_status.side_effect = requests.HTTPError("429")
    monkeypatch.setattr(tmdb.requests, "get", Mock(return_value=response))

    with pytest.raises(tmdb.TMDBResponseError, match="rate limit"):
        tmdb.search_tmdb("Quota")


def test_search_wraps_malformed_json(monkeypatch):
    response = response_with({})
    response.json.side_effect = ValueError("invalid json")
    monkeypatch.setattr(tmdb.requests, "get", Mock(return_value=response))

    with pytest.raises(tmdb.TMDBResponseError, match="invalid response"):
        tmdb.search_tmdb("Malformed")


def test_discover_normalizes_movie_candidates_and_genre_filter(monkeypatch):
    response = response_with(
        {
            "results": [
                {
                    "id": 321,
                    "title": "Popular Movie",
                    "poster_path": "/popular.jpg",
                    "genre_ids": [28, "bad"],
                },
                {"id": "invalid", "title": "Ignored"},
                {"id": 322, "name": "TV-shaped result", "genre_ids": []},
            ]
        }
    )
    request = Mock(return_value=response)
    monkeypatch.setattr(tmdb.requests, "get", request)

    result = tmdb.discover_tmdb("movie", genre_ids=[28, 12, 28])

    assert result == [
        {
            "title": "Popular Movie",
            "tmdb_id": 321,
            "media_type": "movie",
            "genre_ids": [28],
            "poster_url": "https://image.tmdb.org/t/p/w500/popular.jpg",
        },
        {
            "title": "TV-shaped result",
            "tmdb_id": 322,
            "media_type": "movie",
            "genre_ids": [],
            "poster_url": "",
        },
    ]
    assert request.call_args.kwargs["params"]["with_genres"] == "12|28"


def test_discover_rejects_unsupported_media_type():
    with pytest.raises(ValueError, match="Unsupported"):
        tmdb.discover_tmdb("person")


def test_discover_rejects_malformed_results(monkeypatch):
    monkeypatch.setattr(
        tmdb.requests,
        "get",
        Mock(return_value=response_with({"results": {}})),
    )

    with pytest.raises(tmdb.TMDBResponseError, match="invalid response"):
        tmdb.discover_tmdb("tv")
