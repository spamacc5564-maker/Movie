"""
Trending Page
-------------
Displays live trending movies directly from TMDB API (/trending/movie/{time_window}).
Features:
- Time window toggle: Daily ('day') vs Weekly ('week')
- Horizontal scrolling movie carousels (compact, smooth, Netflix-style)
- Expandable deep metadata inspection:
    * Basic info: runtime, certification (US)
    * Content details: genres, overview, keywords, cast, director
    * Performance metrics: vote average, vote count, budget, revenue
"""

import streamlit as st
from utils.ui import load_css, render_navbar, movie_row
from utils.tmdb_client import get_trending_movies, get_movie_details

st.set_page_config(
    page_title="Trending Movies | CinePulse",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Load styling & navbar
load_css()
render_navbar(active_page="Trending")

# Header section with timeframe toggle
h_col1, h_col2 = st.columns([3, 1])
with h_col1:
    st.markdown(
        """
        <div style="margin-bottom: 0.5rem;">
            <h1 style="font-size: 2.1rem; font-weight: 800; margin-bottom: 0.2rem;">🔥 Trending Movies</h1>
            <p style="color: #B3B3B3; font-size: 0.95rem; margin: 0;">
                Live popular films updated in real time via The Movie Database (TMDB) API.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with h_col2:
    time_window = st.radio(
        "Timeframe",
        options=["day", "week"],
        format_func=lambda x: "📅 Today" if x == "day" else "📆 This Week",
        horizontal=True,
    )

# Fetch trending movies
with st.spinner("Fetching trending movies from TMDB..."):
    movies = get_trending_movies(time_window=time_window)

if not movies:
    st.error("No trending movies retrieved. Please ensure your TMDB API key is active.")
else:
    # -------------------------------------------------------------------------
    # 1. Horizontal Carousel Rows (Fixed compact height, smooth horizontal scroll)
    # -------------------------------------------------------------------------
    movie_row("🔥 Top 10 Trending", movies[:10])

    if len(movies) > 10:
        movie_row("⚡ More Trending Hits", movies[10:])

    # -------------------------------------------------------------------------
    # 2. Expandable Metadata Inspector (Kept compact so it doesn't blow out vertical height)
    # -------------------------------------------------------------------------
    with st.expander("🔎 Click to Inspect Full Metadata for Any Trending Movie", expanded=False):
        movie_titles = [f"{m['title']} ({m['year']}) - ★ {m['rating']}" for m in movies]
        selected_idx = st.selectbox(
            "Select a movie to inspect:",
            options=range(len(movies)),
            format_func=lambda i: movie_titles[i],
        )

        if selected_idx is not None:
            sel_movie = movies[selected_idx]
            details = get_movie_details(sel_movie["id"]) or sel_movie

            d_col_poster, d_col_info = st.columns([1, 4])
            with d_col_poster:
                st.image(details["poster"], width=180)

            with d_col_info:
                st.markdown(
                    f"### {details['title']} <span style='color:#B3B3B3; font-size:1.1rem;'>({details['year']})</span>",
                    unsafe_allow_html=True,
                )
                if details.get("tagline"):
                    st.markdown(
                        f"<p style='color:#E50914; font-style:italic; font-size:0.9rem; margin-top:-6px;'>“{details['tagline']}”</p>",
                        unsafe_allow_html=True,
                    )

                cert = details.get("certification", "NR")
                runtime = f"{details.get('runtime')} mins" if details.get("runtime") else "N/A"
                genres_str = details.get("genre_str", "General")
                rating = details.get("rating", "N/A")
                votes = details.get("vote_count", 0)

                st.markdown(
                    f"""
                    <div style="display:flex; gap:12px; align-items:center; margin-bottom:10px; flex-wrap:wrap;">
                        <span style="background:#222; border:1px solid #444; padding:2px 7px; border-radius:4px; font-weight:700; font-size:0.8rem;">{cert}</span>
                        <span style="color:#B3B3B3; font-size:0.85rem;">⏱️ {runtime}</span>
                        <span style="color:#B3B3B3; font-size:0.85rem;">🎭 {genres_str}</span>
                        <span style="color:#46D369; font-weight:700; font-size:0.85rem;">★ {rating} / 10 ({votes:,} votes)</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.write(details.get("overview", "No synopsis available."))

                m_col1, m_col2 = st.columns(2)
                with m_col1:
                    st.markdown(f"**🎬 Director:** {details.get('director', 'Unknown')}")
                    cast_str = ", ".join(details.get("cast", [])[:5]) or "Unknown"
                    st.markdown(f"**🌟 Cast:** {cast_str}")

                with m_col2:
                    budget = details.get("budget", 0)
                    revenue = details.get("revenue", 0)
                    b_str = f"${budget:,.0f}" if budget > 0 else "Not Disclosed"
                    r_str = f"${revenue:,.0f}" if revenue > 0 else "Not Disclosed"
                    st.markdown(f"**💰 Budget:** {b_str}")
                    st.markdown(f"**🎟️ Revenue:** {r_str}")

                if details.get("keywords"):
                    kw_badges = " ".join(
                        [
                            f"<span style='background:#1f1f1f; color:#B3B3B3; padding:2px 8px; border-radius:12px; font-size:0.75rem; margin-right:4px;'>#{k}</span>"
                            for k in details["keywords"][:6]
                        ]
                    )
                    st.markdown(f"<div style='margin-top:8px;'>{kw_badges}</div>", unsafe_allow_html=True)
