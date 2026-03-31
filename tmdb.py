import os
import json
from typing import Any, Dict, List, Optional

from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


class TMDBError(RuntimeError):
    pass


class TMDBClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = "https://api.themoviedb.org/3",
        image_base_url: str = "https://image.tmdb.org/t/p",
        timeout_s: float = 15.0,
    ) -> None:
        self.api_key = api_key or os.getenv("TMDB_API_KEY", "")
        if not self.api_key:
            raise TMDBError("TMDB_API_KEY is not set")

        self.base_url = base_url.rstrip("/")
        self.image_base_url = image_base_url.rstrip("/")
        self.timeout_s = timeout_s

    def _get(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        q = dict(params or {})
        q["api_key"] = self.api_key
        url = f"{self.base_url}/{path.lstrip('/')}?{urlencode(q)}"

        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
        except HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                body = ""
            msg = None
            try:
                msg = json.loads(body).get("status_message") if body else None
            except Exception:
                msg = None
            raise TMDBError(f"TMDB HTTP {e.code}: {msg or body or e.reason}") from e
        except URLError as e:
            raise TMDBError(f"TMDB request failed: {e.reason}") from e
        except Exception as e:
            raise TMDBError(f"TMDB request failed: {e}") from e

        try:
            return json.loads(raw) if raw else {}
        except ValueError as e:
            raise TMDBError("TMDB returned invalid JSON") from e

    def poster_url(self, poster_path: Optional[str], *, size: str = "w500") -> Optional[str]:
        if not poster_path:
            return None
        if not poster_path.startswith("/"):
            poster_path = "/" + poster_path
        return f"{self.image_base_url}/{size}{poster_path}"

    def search_movie(self, query: str, *, year: Optional[int] = None, include_adult: bool = False) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"query": query, "include_adult": include_adult}
        if year is not None:
            params["year"] = int(year)
        data = self._get("/search/movie", params=params)
        return list(data.get("results") or [])

    def get_movie(self, tmdb_id: int) -> Dict[str, Any]:
        return self._get(f"/movie/{int(tmdb_id)}", params={"append_to_response": "credits"})

    def get_movie_min(self, tmdb_id: int) -> Dict[str, Any]:
        m = self.get_movie(tmdb_id)
        return {
            "tmdb_id": m.get("id"),
            "title": m.get("title") or m.get("original_title"),
            "release_date": m.get("release_date"),
            "poster_url": self.poster_url(m.get("poster_path")),
            "overview": m.get("overview"),
        }


_default_client: Optional[TMDBClient] = None


def client() -> TMDBClient:
    global _default_client
    if _default_client is None:
        _default_client = TMDBClient()
    return _default_client


def search_movie(query: str, *, year: Optional[int] = None, include_adult: bool = False) -> List[Dict[str, Any]]:
    return client().search_movie(query, year=year, include_adult=include_adult)


def get_movie(tmdb_id: int) -> Dict[str, Any]:
    return client().get_movie(tmdb_id)


def get_movie_min(tmdb_id: int) -> Dict[str, Any]:
    return client().get_movie_min(tmdb_id)

