import os
import requests
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

def search_tmdb(title):
    try:
        response = requests.get(
            "https://api.themoviedb.org/3/search/multi",
            params={
                "api_key": TMDB_API_KEY,
                "query": title,
                "include_adult": "false"
            }
        )
        data = response.json()
        results = data.get("results", [])

        # Filter out people — endpoint returns actors/directors too
        results = [r for r in results if r.get("media_type") != "person"]

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
            "media_type": media_type
        }

    except Exception:
        return None