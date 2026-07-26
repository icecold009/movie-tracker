import logging

import requests

from config import TMDB_API_KEY


logger = logging.getLogger(__name__)
TMDB_REQUEST_TIMEOUT_SECONDS = 5


class TMDBError(Exception):
    """Base class for safe, user-visible TMDB integration failures."""


class TMDBRequestError(TMDBError):
    pass


class TMDBResponseError(TMDBError):
    pass


def search_tmdb(title):
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

    if not results:
        return None

    result = results[0]
    media_type = result.get("media_type", "movie")
    full_title = result.get("title") or result.get("name") or title
    poster_path = result.get("poster_path")
    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""

    return {
        "full_title": full_title,
        "poster_url": poster_url,
        "media_type": media_type,
    }
