"""
CinePulse - Movie Recommendation Web App
Main Entry Point
========================================
Integrates live TMDB API metadata with our Netflix-themed design system.
Fetches real-time trending, top-rated, and popular movies with cached calls.
Falls back gracefully to curated sample data if the API is unreachable.
"""

import streamlit as st
from utils.ui import (
    load_css,
    render_navbar,
    render_hero_banner,
    render_filter_console,
    movie_row,
    SAMPLE_TRENDING_MOVIES,
    SAMPLE_TOP_RATED_MOVIES,
    SAMPLE_RECOMMENDED_MOVIES,
)
from utils.tmdb_client import (
    get_api_key,
    get_trending_movies,
    get_top_rated_movies,
    get_popular_movies,
)

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="CinePulse - Discover & Recommend Movies",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# 2. Inject Netflix-Style CSS
# -----------------------------------------------------------------------------
load_css()

# -----------------------------------------------------------------------------
# 3. Top Navigation Bar (Original Red Wordmark + Page Links)
# -----------------------------------------------------------------------------
render_navbar(active_page="Home")

# -----------------------------------------------------------------------------
# 4. Fetch Live TMDB Data (with Caching & Graceful Fallback)
# -----------------------------------------------------------------------------
api_key = get_api_key()
api_connected = False

trending_movies = []
top_rated_movies = []
popular_movies = []

if api_key:
    try:
        trending_movies = get_trending_movies(time_window="day")
        top_rated_movies = get_top_rated_movies(page=1)
        popular_movies = get_popular_movies(page=1)
        if trending_movies:
            api_connected = True
    except Exception as e:
        st.warning(f"Unable to reach TMDB API: {e}")

# Fallback to curated samples if live data is not available
display_trending = trending_movies if trending_movies else SAMPLE_TRENDING_MOVIES
display_top_rated = top_rated_movies if top_rated_movies else SAMPLE_TOP_RATED_MOVIES
display_popular = popular_movies if popular_movies else SAMPLE_RECOMMENDED_MOVIES

# -----------------------------------------------------------------------------
# 5. Dynamic Hero Billboard Banner
# -----------------------------------------------------------------------------
# Choose the #1 trending title with a backdrop, or fall back to default spotlight
hero_movie = None
for m in display_trending:
    if m.get("backdrop"):
        hero_movie = m
        break

render_hero_banner(hero_movie)

# -----------------------------------------------------------------------------
# 6. Rectangular Filter Console (Core Filters Above Trending Today)
# -----------------------------------------------------------------------------
filtered_results = render_filter_console(key_prefix="home")
if filtered_results is not None:
    if filtered_results:
        movie_row(
            title=f"🎯 Filtered Results ({len(filtered_results)} matches found)",
            movies=filtered_results,
        )
    else:
        st.info("No movies matched your exact criteria. Try broadening your rating or runtime threshold.")

# -----------------------------------------------------------------------------
# 7. Live Horizontal Scrolling Movie Rows
# -----------------------------------------------------------------------------
# Row 1: Trending Now (Live TMDB /trending/movie/day)
movie_row(
    title="🔥 Trending Today",
    movies=display_trending,
    see_all_link="/Trending",
)

# Row 2: Top Rated of All Time (Live TMDB /movie/top_rated)
movie_row(
    title="⭐ Top Rated of All Time",
    movies=display_top_rated,
    see_all_link="/Trending",
)

# Row 3: Popular Movies (Live TMDB /movie/popular)
movie_row(
    title="🍿 Popular Releases",
    movies=display_popular,
    see_all_link="/Search",
)

# -----------------------------------------------------------------------------
# 7. Sidebar (API Status & Quick Filters)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎬 **CinePulse**")
    if api_connected:
        st.markdown(
            "<span style='color:#46D369; font-weight:700;'>● TMDB API Connected</span>",
            unsafe_allow_html=True,
        )
        st.caption(f"Loaded {len(display_trending)} trending & {len(display_top_rated)} top-rated titles.")
    else:
        st.markdown(
            "<span style='color:#E50914; font-weight:700;'>● Offline Mode</span>",
            unsafe_allow_html=True,
        )
        st.caption("Displaying cached/sample movie data.")

    st.markdown("---")
    st.markdown("#### **Quick Search**")
    quick_query = st.text_input("Find a movie", placeholder="e.g. Inception, Dune...")
    if quick_query:
        st.info(f"Go to the **Search** tab to explore all results for '{quick_query}'!")
