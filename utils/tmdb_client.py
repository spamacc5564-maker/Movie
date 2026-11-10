"""
TMDB API Client Module
----------------------
Handles data retrieval from The Movie Database (TMDB) API v3.
Features:
- Secure API key retrieval from st.secrets or environment variables.
- Result caching using @st.cache_data to prevent redundant calls and respect rate limits.
- Robust error handling (graceful fallback on connection/auth errors).
- Retrieval of:
    * Basic info (title, release date/year, runtime, certification)
    * Content details (plot summary, genres, keywords, cast, director)
    * Performance metrics (vote average, vote count, budget, revenue)
    * Advanced discovery & filtering (temporal, quality, genre AND/OR, personnel)
"""

import os
from typing import Any
import requests
import streamlit as st

# Base TMDB URLs
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original"
FALLBACK_POSTER = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&auto=format&fit=crop&q=60"


def get_api_key() -> str | None:
    """
    Safely retrieves the TMDB API key.
    Checks:
    1. st.secrets (when running inside Streamlit)
    2. os.environ['TMDB_API_KEY']
    3. Direct reading of .streamlit/secrets.toml (for scripts/tests outside Streamlit)
    """
    try:
        if "TMDB_API_KEY" in st.secrets and st.secrets["TMDB_API_KEY"]:
            return str(st.secrets["TMDB_API_KEY"]).strip()
    except Exception:
        pass

    env_key = os.environ.get("TMDB_API_KEY")
    if env_key:
        return env_key.strip()

    # Fallback: Read directly from .streamlit/secrets.toml
    try:
        import tomllib
        from pathlib import Path

        secrets_file = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
        if secrets_file.exists():
            with open(secrets_file, "rb") as f:
                data = tomllib.load(f)
            key = data.get("TMDB_API_KEY")
            if key and key not in ["paste_your_api_key_here", "YOUR_KEY"]:
                return str(key).strip()
    except Exception:
        pass

    return None


@st.cache_data(ttl=3600, show_spinner=False)
def _tmdb_get(endpoint: str, params: tuple[tuple[str, Any], ...] | None = None) -> dict[str, Any] | None:
    """
    Low-level cached GET request to TMDB API.
    Params are passed as a tuple of pairs so they are hashable by st.cache_data.
    """
    api_key = get_api_key()
    if not api_key:
        return None

    query_params: dict[str, Any] = {"api_key": api_key}
    if params:
        query_params.update(dict(params))

    url = f"{TMDB_BASE_URL}/{endpoint.lstrip('/')}"
    try:
        response = requests.get(url, params=query_params, timeout=8)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            st.error("Invalid TMDB API Key. Please verify .streamlit/secrets.toml.")
            return None
        else:
            return None
    except requests.RequestException:
        return None


def format_movie_data(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Transforms raw TMDB movie payload into a normalized dictionary
    compatible with the UI components (movie_card, movie_row, hero_banner).
    """
    poster_path = raw.get("poster_path")
    backdrop_path = raw.get("backdrop_path")
    release_date = raw.get("release_date") or ""
    year = release_date[:4] if len(release_date) >= 4 else "N/A"
    rating = round(float(raw.get("vote_average", 0.0)), 1)

    return {
        "id": raw.get("id"),
        "title": raw.get("title") or raw.get("name") or "Untitled",
        "year": year,
        "rating": rating,
        "vote_count": raw.get("vote_count", 0),
        "popularity": raw.get("popularity", 0.0),
        "overview": raw.get("overview", "No synopsis available."),
        "poster": f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else FALLBACK_POSTER,
        "backdrop": f"{TMDB_BACKDROP_BASE_URL}{backdrop_path}" if backdrop_path else None,
        "tag": f"{int(rating * 10)}% Match" if rating > 0 else "",
        "genre_ids": raw.get("genre_ids", []),
    }


# ---------------------------------------------------------------------------
# High-Level TMDB Retrieval Functions
# ---------------------------------------------------------------------------


def get_trending_movies(time_window: str = "day") -> list[dict[str, Any]]:
    """
    Retrieves trending movies for the given time window ('day' or 'week').
    """
    endpoint = f"trending/movie/{time_window}"
    data = _tmdb_get(endpoint)
    if not data or "results" not in data:
        return []
    return [format_movie_data(m) for m in data["results"] if m.get("poster_path")]


def get_popular_movies(page: int = 1) -> list[dict[str, Any]]:
    """Retrieves current popular movies on TMDB."""
    params = (("page", page),)
    data = _tmdb_get("movie/popular", params)
    if not data or "results" not in data:
        return []
    return [format_movie_data(m) for m in data["results"] if m.get("poster_path")]


def get_top_rated_movies(page: int = 1) -> list[dict[str, Any]]:
    """Retrieves all-time top rated movies on TMDB."""
    params = (("page", page),)
    data = _tmdb_get("movie/top_rated", params)
    if not data or "results" not in data:
        return []
    return [format_movie_data(m) for m in data["results"] if m.get("poster_path")]


def search_movies(query: str, page: int = 1) -> list[dict[str, Any]]:
    """
    Searches movies by title query.
    """
    if not query.strip():
        return []
    params = (
        ("query", query.strip()),
        ("page", page),
        ("include_adult", False),
    )
    data = _tmdb_get("search/movie", params)
    if not data or "results" not in data:
        return []
    return [format_movie_data(m) for m in data["results"]]


def get_movie_details(movie_id: int) -> dict[str, Any] | None:
    """
    Retrieves deep metadata for a single movie including:
    - Basic info: runtime, certification, budget, revenue
    - Content details: genres, overview, keywords, cast (top 8), director
    - Performance metrics: vote average, vote count
    """
    params = (
        ("append_to_response", "credits,keywords,release_dates"),
    )
    data = _tmdb_get(f"movie/{movie_id}", params)
    if not data:
        return None

    # Base formatted details
    movie = format_movie_data(data)

    # Runtime & Financials
    movie["runtime"] = data.get("runtime")  # Minutes
    movie["budget"] = data.get("budget", 0)
    movie["revenue"] = data.get("revenue", 0)
    movie["status"] = data.get("status", "")
    movie["tagline"] = data.get("tagline", "")

    # Genres (list of names)
    genres = [g["name"] for g in data.get("genres", [])]
    movie["genres"] = genres
    movie["genre_str"] = " • ".join(genres) if genres else "General"

    # US Certification (e.g. PG-13, R)
    cert = "NR"
    release_dates = data.get("release_dates", {}).get("results", [])
    for rd in release_dates:
        if rd.get("iso_3166_1") == "US":
            for release in rd.get("release_dates", []):
                if release.get("certification"):
                    cert = release["certification"]
                    break
    movie["certification"] = cert

    # Credits: Cast and Director
    credits_data = data.get("credits", {})
    cast_list = [c["name"] for c in credits_data.get("cast", [])[:8]]
    movie["cast"] = cast_list

    directors = [c["name"] for c in credits_data.get("crew", []) if c.get("job") == "Director"]
    movie["director"] = directors[0] if directors else "Unknown"

    # Keywords (for NLP and tag exploration)
    keywords_data = data.get("keywords", {}).get("keywords", [])
    movie["keywords"] = [k["name"] for k in keywords_data]

    return movie


@st.cache_data(ttl=86400, show_spinner=False)
def get_genre_map() -> dict[int, str]:
    """Retrieves genre ID to genre name mapping (cached 24 hrs)."""
    data = _tmdb_get("genre/movie/list")
    if not data or "genres" not in data:
        return {}
    return {g["id"]: g["name"] for g in data["genres"]}


def search_person(name: str) -> int | None:
    """
    Looks up an actor or director by name and returns their TMDB person ID.
    Used for personnel filtering in the discovery engine.
    """
    if not name or not name.strip():
        return None
    params = (
        ("query", name.strip()),
        ("include_adult", False),
    )
    data = _tmdb_get("search/person", params)
    if data and data.get("results"):
        return data["results"][0].get("id")
    return None


def discover_movies(
    year_range: tuple[int, int] | None = None,
    min_rating: float | None = None,
    min_vote_count: int | None = None,
    with_genres: list[int] | None = None,
    genre_operator: str = "AND",  # "AND" (comma) or "OR" (pipe)
    runtime_range: tuple[int, int] | None = None,
    certification: str | None = None,
    person_id: int | None = None,
    original_language: str | None = None,
    sort_by: str = "popularity.desc",
    page: int = 1,
) -> list[dict[str, Any]]:
    """
    Advanced TMDB Movie Discovery implementing all core assignment filters:
    - Temporal: year range
    - Quality: min rating, min vote count
    - Content: runtime, certification, language
    - Personnel: actor/director ID
    - Genre combinations with logical operators (AND/OR)
    """
    param_list: list[tuple[str, Any]] = [
        ("sort_by", sort_by),
        ("include_adult", False),
        ("page", page),
    ]

    # Temporal filters
    if year_range:
        start_year, end_year = year_range
        param_list.append(("primary_release_date.gte", f"{start_year}-01-01"))
        param_list.append(("primary_release_date.lte", f"{end_year}-12-31"))

    # Quality filters
    if min_rating is not None and min_rating > 0:
        param_list.append(("vote_average.gte", min_rating))
    if min_vote_count is not None and min_vote_count > 0:
        param_list.append(("vote_count.gte", min_vote_count))

    # Runtime filters
    if runtime_range:
        min_rt, max_rt = runtime_range
        if min_rt > 0:
            param_list.append(("with_runtime.gte", min_rt))
        if max_rt > 0:
            param_list.append(("with_runtime.lte", max_rt))

    # Certification
    if certification and certification != "All":
        param_list.append(("certification_country", "US"))
        param_list.append(("certification", certification))

    # Personnel (Actor / Director)
    if person_id:
        param_list.append(("with_people", person_id))

    # Language
    if original_language and original_language != "all":
        param_list.append(("with_original_language", original_language))

    # Genre combinations (AND vs OR)
    if with_genres:
        separator = "," if genre_operator == "AND" else "|"
        param_list.append(("with_genres", separator.join(str(g) for g in with_genres)))

    data = _tmdb_get("discover/movie", tuple(param_list))
    if not data or "results" not in data:
        return []
    return [format_movie_data(m) for m in data["results"] if m.get("poster_path")]


def get_similar_movies(movie_id: int) -> list[dict[str, Any]]:
    """Retrieves similar movies directly from TMDB."""
    data = _tmdb_get(f"movie/{movie_id}/similar")
    if not data or "results" not in data:
        return []
    return [format_movie_data(m) for m in data["results"] if m.get("poster_path")]
