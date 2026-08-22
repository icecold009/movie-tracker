import logging
import time
from collections import deque
from threading import Lock

import requests

from config import TMDB_API_KEY
from observability import log_event


logger = logging.getLogger(__name__)
TMDB_REQUEST_TIMEOUT_SECONDS = 5
TMDB_CACHE_TTL_SECONDS = 300
TMDB_RATE_LIMIT_WINDOW_SECONDS = 60
TMDB_RATE_LIMIT_MAX_REQUESTS = 30

_cache = {}
_request_times = deque()
_state_lock = Lock()


class TMDBError(Exception):
    """Base class for safe, user-visible TMDB integration failures."""


class TMDBRequestError(TMDBError):
    pass


class TMDBResponseError(TMDBError):
    pass


class TMDBRateLimitError(TMDBError):
    pass


def _cache_key(title):
    return " ".join(title.split()).casefold()


def _get_cached(key, now):
    with _state_lock:
        cached = _cache.get(key)
        if cached is None:
            return False, None
        expires_at, result = cached
        if expires_at <= now:
            del _cache[key]
            return False, None
        return True, result


def _set_cached(key, result, now):
    with _state_lock:
        _cache[key] = (now + TMDB_CACHE_TTL_SECONDS, result)


def _enforce_rate_limit(now):
    with _state_lock:
        cutoff = now - TMDB_RATE_LIMIT_WINDOW_SECONDS
        while _request_times and _request_times[0] <= cutoff:
            _request_times.popleft()
        if len(_request_times) >= TMDB_RATE_LIMIT_MAX_REQUESTS:
            raise TMDBRateLimitError("Search rate limit reached. Try again later.")
        _request_times.append(now)


def _request_json(url, params):
    try:
        response = requests.get(url, params=params, timeout=TMDB_REQUEST_TIMEOUT_SECONDS)
    except requests.Timeout as exc:
        log_event(logger, logging.WARNING, "tmdb.request_timeout", provider="tmdb")
        raise TMDBRequestError("TMDB took too long to respond. Try again later.") from exc
    except requests.RequestException as exc:
        log_event(
            logger,
            logging.WARNING,
            "tmdb.request_failed",
            exception_type=type(exc).__name__,
            provider="tmdb",
        )
        raise TMDBRequestError("TMDB is temporarily unavailable. Try again later.") from exc

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = response.status_code
        log_event(
            logger,
            logging.WARNING,
            "tmdb.http_error",
            provider="tmdb",
            status_code=status_code,
        )
        if status_code in (401, 403):
            message = "TMDB rejected the server API configuration."
        elif status_code == 429:
            message = "TMDB rate limit reached. Try again later."
        else:
            message = "TMDB returned an error. Try again later."
        raise TMDBResponseError(message) from exc

    try:
        return response.json()
    except (TypeError, ValueError) as exc:
        log_event(logger, logging.WARNING, "tmdb.malformed_json", provider="tmdb")
        raise TMDBResponseError("TMDB returned an invalid response.") from exc


def search_tmdb(title):
    key = _cache_key(title)
    now = time.monotonic()
    found, cached_result = _get_cached(key, now)
    if found:
        return cached_result

    _enforce_rate_limit(now)
    data = _request_json(
        "https://api.themoviedb.org/3/search/multi",
        {
            "api_key": TMDB_API_KEY,
            "query": title,
            "include_adult": "false",
        },
    )

    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        log_event(logger, logging.WARNING, "tmdb.invalid_search_shape", provider="tmdb")
        raise TMDBResponseError("TMDB returned an invalid response.")

    # Filter out people; the multi-search endpoint returns actors/directors too.
    results = [
        result for result in results
        if isinstance(result, dict) and result.get("media_type") != "person"
    ]

    result = None
    if results:
        first_result = results[0]
        media_type = first_result.get("media_type", "movie")
        full_title = first_result.get("title") or first_result.get("name") or title
        poster_path = first_result.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
        tmdb_id = first_result.get("id")
        if not isinstance(tmdb_id, int):
            tmdb_id = None
        genre_ids = [
            genre_id
            for genre_id in first_result.get("genre_ids", [])
            if isinstance(genre_id, int)
        ]
        synopsis = first_result.get("overview")
        if not isinstance(synopsis, str):
            synopsis = ""
        release_date = first_result.get("release_date") or first_result.get("first_air_date")
        if not isinstance(release_date, str) or not release_date.strip():
            release_date = None
        result = {
            "full_title": full_title,
            "poster_url": poster_url,
            "media_type": media_type,
            "tmdb_id": tmdb_id,
            "genre_ids": genre_ids,
            "synopsis": synopsis.strip(),
            "release_date": release_date,
        }

    _set_cached(key, result, now)
    return result


def discover_tmdb(media_type, genre_ids=()):
    """Return normalized popular TMDB candidates for movie or TV discovery."""
    if media_type not in {"movie", "tv"}:
        raise ValueError("Unsupported TMDB media type")

    normalized_genres = tuple(sorted({genre_id for genre_id in genre_ids if isinstance(genre_id, int)}))
    key = f"discover:{media_type}:{','.join(map(str, normalized_genres))}"
    now = time.monotonic()
    found, cached_result = _get_cached(key, now)
    if found:
        return cached_result

    _enforce_rate_limit(now)
    params = {
        "api_key": TMDB_API_KEY,
        "include_adult": "false",
        "sort_by": "popularity.desc",
    }
    if normalized_genres:
        params["with_genres"] = "|".join(map(str, normalized_genres))
    data = _request_json(f"https://api.themoviedb.org/3/discover/{media_type}", params)
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        log_event(logger, logging.WARNING, "tmdb.invalid_discovery_shape", provider="tmdb")
        raise TMDBResponseError("TMDB returned an invalid response.")

    candidates = []
    for item in results:
        if not isinstance(item, dict) or not isinstance(item.get("id"), int):
            continue
        title = item.get("title") or item.get("name")
        if not isinstance(title, str) or not title.strip():
            continue
        poster_path = item.get("poster_path")
        synopsis = item.get("overview")
        if not isinstance(synopsis, str):
            synopsis = ""
        release_date = item.get("release_date") or item.get("first_air_date")
        if not isinstance(release_date, str) or not release_date.strip():
            release_date = None
        candidates.append({
            "title": title,
            "tmdb_id": item["id"],
            "media_type": media_type,
            "genre_ids": [genre_id for genre_id in item.get("genre_ids", []) if isinstance(genre_id, int)],
            "poster_url": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "",
            "synopsis": synopsis.strip(),
            "release_date": release_date,
        })

    _set_cached(key, candidates, now)
    return candidates
