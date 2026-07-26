import logging
import time
from collections import deque
from threading import Lock

import requests

from config import TMDB_API_KEY


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


def search_tmdb(title):
    key = _cache_key(title)
    now = time.monotonic()
    found, cached_result = _get_cached(key, now)
    if found:
        return cached_result

    _enforce_rate_limit(now)
    try:
        response = requests.get(
            "https://api.themoviedb.org/3/search/multi",
            params={
                "api_key": TMDB_API_KEY,
                "query": title,
                "include_adult": "false",
            },
            timeout=TMDB_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        logger.warning("TMDB request timed out")
        raise TMDBRequestError("TMDB took too long to respond. Try again later.") from exc
    except requests.RequestException as exc:
        logger.warning("TMDB request failed: %s", type(exc).__name__)
        raise TMDBRequestError("TMDB is temporarily unavailable. Try again later.") from exc

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = response.status_code
        logger.warning("TMDB returned HTTP status %s", status_code)
        if status_code in (401, 403):
            message = "TMDB rejected the server API configuration."
        elif status_code == 429:
            message = "TMDB rate limit reached. Try again later."
        else:
            message = "TMDB returned an error. Try again later."
        raise TMDBResponseError(message) from exc

    try:
        data = response.json()
    except (TypeError, ValueError) as exc:
        logger.warning("TMDB returned malformed JSON")
        raise TMDBResponseError("TMDB returned an invalid response.") from exc

    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        logger.warning("TMDB response did not contain a results list")
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
        result = {
            "full_title": full_title,
            "poster_url": poster_url,
            "media_type": media_type,
        }

    _set_cached(key, result, now)
    return result
