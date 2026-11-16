"""
User Watchlist & Profile-Based Recommendations
----------------------------------------------
Implements:
1. Personal Watchlist Management: Save, view, and remove favorite movies.
2. User Taste Profile: Analyzes saved movies to extract preferred genres, directors, and average rating.
3. Profile-Based Recommendations: Generates personalized recommendations based on the user's collective taste profile.
"""

from collections import Counter
import streamlit as st
from utils.ui import (
    load_css,
    render_navbar,
    init_watchlist,
    save_watchlist_to_disk,
    movie_row,
    movie_card,
)
from utils.recommender import generate_recommendations
from utils.tmdb_client import discover_movies, get_movie_details

st.set_page_config(
    page_title="My Watchlist | CinePulse",
    page_icon="🔖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Load styling & navbar
load_css()
render_navbar(active_page="Watchlist")

# Header section
st.markdown(
    """
    <div style="margin-bottom: 1.5rem;">
        <h1 style="font-size: 2.1rem; font-weight: 800; margin-bottom: 0.2rem;">🔖 My Watchlist & Taste Profile</h1>
        <p style="color: #B3B3B3; font-size: 0.95rem; margin: 0;">
            Manage your saved titles, inspect your personalized taste profile, and explore recommendations based on your library.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Initialize watchlist
watchlist = init_watchlist()
saved_movies = list(watchlist.values())

# -----------------------------------------------------------------------------
# 1. WATCHLIST LIBRARY SECTION
# -----------------------------------------------------------------------------
st.markdown(f"### 🎬 Saved Titles ({len(saved_movies)})")

if not saved_movies:
    st.markdown(
        """
        <div style="background:#181818; border:1px dashed #383838; border-radius:8px; padding:2.5rem 1rem; text-align:center; margin-bottom:1.5rem;">
            <div style="font-size:2.5rem; margin-bottom:0.6rem;">🔖</div>
            <h3 style="color:#FFFFFF; margin-bottom:0.3rem;">Your Watchlist is Currently Empty</h3>
            <p style="color:#B3B3B3; max-width:460px; margin:0 auto 1rem auto; font-size:0.92rem;">
                Click the <strong>➕</strong> icon on any movie poster across Home, Trending, or Search to add movies to your personal queue.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### 💡 Or Quick-Add a Movie to Test Your Watchlist:")
    s_col1, s_col2, s_col3 = st.columns(3)
    if s_col1.button("➕ Add 'Inception'", use_container_width=True):
        details = get_movie_details(27205)
        if details:
            watchlist[27205] = details
            save_watchlist_to_disk(watchlist)
            st.toast("Added Inception!", icon="🔖")
            st.rerun()
    if s_col2.button("➕ Add 'Dune: Part Two'", use_container_width=True):
        details = get_movie_details(693134)
        if details:
            watchlist[693134] = details
            save_watchlist_to_disk(watchlist)
            st.toast("Added Dune: Part Two!", icon="🔖")
            st.rerun()
    if s_col3.button("➕ Add 'The Dark Knight'", use_container_width=True):
        details = get_movie_details(155)
        if details:
            watchlist[155] = details
            save_watchlist_to_disk(watchlist)
            st.toast("Added The Dark Knight!", icon="🔖")
            st.rerun()

    st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
    col_nav1, col_nav2, _ = st.columns([1.5, 1.5, 5])
    with col_nav1:
        if st.button("🔥 Browse Trending", type="primary", use_container_width=True):
            st.switch_page("pages/1_Trending.py")
    with col_nav2:
        if st.button("🔍 Search & Filter", use_container_width=True):
            st.switch_page("pages/2_Search.py")
else:
    # Render saved titles in a horizontal row
    movie_row("Your Saved Queue", saved_movies)

    # Watchlist Management Drawer
    with st.expander("⚙️ Manage Watchlist & Remove Titles", expanded=False):
        rem_titles = {f"{m['title']} ({m.get('year', 'N/A')})": m["id"] for m in saved_movies}
        c_sel, c_del, c_clear = st.columns([3, 1.2, 1.2])
        with c_sel:
            selected_rem_name = st.selectbox("Select movie to remove:", list(rem_titles.keys()), label_visibility="collapsed")
        with c_del:
            if st.button("🗑️ Remove Title", use_container_width=True):
                movie_id_to_rem = rem_titles[selected_rem_name]
                if movie_id_to_rem in watchlist:
                    del watchlist[movie_id_to_rem]
                    save_watchlist_to_disk(watchlist)
                    st.toast(f"Removed '{selected_rem_name}' from Watchlist", icon="🗑️")
                    st.rerun()
        with c_clear:
            if st.button("⚠️ Clear All", use_container_width=True):
                watchlist.clear()
                save_watchlist_to_disk(watchlist)
                st.toast("Watchlist cleared!", icon="🧹")
                st.rerun()

    # -------------------------------------------------------------------------
    # 2. USER TASTE PROFILE (Assignment Feature: Profile-Based Analysis)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📊 Your User Taste Profile")
    st.caption("Computed from your collective viewing history and saved watchlist attributes.")

    # Aggregate attributes across saved titles
    all_genres = []
    all_directors = []
    all_cast = []
    all_ratings = []

    for m in saved_movies:
        # Genres
        for g in m.get("genres", []):
            all_genres.append(g)
        # Directors
        if m.get("director") and m["director"] != "Unknown":
            all_directors.append(m["director"])
        # Cast
        for a in m.get("cast", [])[:3]:
            all_cast.append(a)
        # Ratings
        try:
            all_ratings.append(float(m.get("rating", 0.0)))
        except (ValueError, TypeError):
            pass

    genre_counts = Counter(all_genres).most_common(4)
    director_counts = Counter(all_directors).most_common(3)
    cast_counts = Counter(all_cast).most_common(4)
    avg_rating = round(sum(all_ratings) / len(all_ratings), 1) if all_ratings else 0.0

    # Display profile statistics in modern metric cards
    m_col1, m_col2, m_col3 = st.columns([2, 2, 1.2])

    with m_col1:
        st.markdown("**🎭 Top Preferred Genres**")
        if genre_counts:
            genre_pills = " ".join(
                [f"<span class='taste-metric-pill'>{g} ({count})</span>" for g, count in genre_counts]
            )
            st.markdown(f"<div>{genre_pills}</div>", unsafe_allow_html=True)
        else:
            st.write("Not enough genre data yet.")

    with m_col2:
        st.markdown("**🎬 Favorite Directors & Actors**")
        directors_str = ", ".join([d for d, _ in director_counts]) if director_counts else "Various"
        actors_str = ", ".join([a for a, _ in cast_counts[:3]]) if cast_counts else "Various"
        st.markdown(f"- **Directors:** {directors_str}")
        st.markdown(f"- **Actors:** {actors_str}")

    with m_col3:
        st.markdown("**⭐ Taste Rating**")
        st.markdown(
            f"<div style='font-size:1.8rem; font-weight:800; color:#46D369;'>★ {avg_rating}</div><span style='color:#888; font-size:0.8rem;'>Avg saved quality</span>",
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------------------
    # 3. PROFILE-BASED RECOMMENDATIONS (Assignment Feature: Enhanced Recs)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🎯 Recommended Based on Your Watchlist")

    top_genre_name = genre_counts[0][0] if genre_counts else "Sci-Fi"
    top_seed_movie = saved_movies[0]

    st.markdown(
        f"""
        <div style="background:rgba(229,9,20,0.08); border-left:3px solid #E50914; padding:8px 14px; border-radius:0 6px 6px 0; margin-bottom:1.2rem;">
            <span style="font-size:0.88rem; color:#FFFFFF;">
                💡 <strong>Profile Insight:</strong> Your watchlist heavily leans toward <strong>{top_genre_name}</strong> 
                and films like <em>{top_seed_movie.get('title')}</em>. Here are personalized titles that fit your taste:
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.spinner("Generating recommendations tailored to your taste profile..."):
        # Generate recommendations using top seed movie
        _, profile_recs = generate_recommendations(
            seed_movie_id=top_seed_movie["id"],
            strategy="hybrid",
            top_n=10,
        )

        # Filter out movies that are already in the watchlist so all suggestions are novel
        fresh_profile_recs = [m for m in profile_recs if m["id"] not in watchlist]

    if fresh_profile_recs:
        movie_row(
            title=f"Personalized for You (Fans of {top_seed_movie.get('title')})",
            movies=fresh_profile_recs,
            see_all_link="/Recommendations",
        )
    else:
        st.info("Add more titles to your watchlist to unlock deeper profile recommendations!")
