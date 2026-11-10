"""
Search & Filter Page
--------------------
Provides full movie search and all 5 core assignment filtering capabilities:
1. Temporal filters: Year/decade ranges, release periods
2. Quality thresholds: Minimum TMDB ratings, vote count requirements
3. Content specifications: Runtime brackets, US certifications, language
4. Personnel: Actor and Director name lookup
5. Genre combinations with logical operators (AND / OR)
"""

import streamlit as st
from utils.ui import load_css, render_navbar, render_filter_console, movie_row, movie_card
from utils.tmdb_client import search_movies, get_movie_details

st.set_page_config(
    page_title="Search & Filter | CinePulse",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Load styling & navbar
load_css()
render_navbar(active_page="Search")

# Page Header
st.markdown(
    """
    <div style="margin-bottom: 1.5rem;">
        <h1 style="font-size: 2.1rem; font-weight: 800; margin-bottom: 0.2rem;">🔍 Search & Discover Movies</h1>
        <p style="color: #B3B3B3; font-size: 0.95rem; margin: 0;">
            Search titles by keyword or apply multi-dimensional filters across genres, years, ratings, and cast/crew.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Tab toggle: Keyword Search vs Advanced Filter Console
tab_filter, tab_keyword = st.tabs(["🎛️ Advanced Core Filters", "🔎 Keyword Title Search"])

with tab_keyword:
    search_query = st.text_input(
        "Search by Title or Keyword",
        placeholder="e.g. Inception, Interstellar, Batman, Spider-Man...",
        key="search_tab_query",
    )
    if search_query.strip():
        with st.spinner(f"Searching for '{search_query}'..."):
            search_results = search_movies(search_query)

        if search_results:
            st.caption(f"Found **{len(search_results)}** matching titles.")
            movie_row(f"Results for '{search_query}'", search_results)
        else:
            st.info(f"No movies found matching '{search_query}'. Try a different keyword.")

with tab_filter:
    # Renders the rectangular filter console
    filtered_movies = render_filter_console(key_prefix="search_page")

    if filtered_movies is not None:
        if filtered_movies:
            st.markdown(f"### 🎯 Filtered Results ({len(filtered_movies)} titles found)")
            movie_row("Top Matches", filtered_movies[:10])
            if len(filtered_movies) > 10:
                movie_row("More Discoveries", filtered_movies[10:])

            # Expandable movie inspector for search results
            with st.expander("🔎 Click to Inspect Metadata for any Result", expanded=False):
                res_titles = [f"{m['title']} ({m['year']}) - ★ {m['rating']}" for m in filtered_movies]
                s_idx = st.selectbox(
                    "Choose a movie:",
                    options=range(len(filtered_movies)),
                    format_func=lambda i: res_titles[i],
                    key="search_res_inspector",
                )
                if s_idx is not None:
                    sel_res = filtered_movies[s_idx]
                    details = get_movie_details(sel_res["id"]) or sel_res

                    d_col1, d_col2 = st.columns([1, 4])
                    with d_col1:
                        st.image(details["poster"], width=170)
                    with d_col2:
                        st.markdown(f"### {details['title']} ({details['year']})")
                        if details.get("tagline"):
                            st.caption(f"“{details['tagline']}”")
                        st.markdown(
                            f"**Cert:** `{details.get('certification', 'NR')}` | **Runtime:** `{details.get('runtime', 'N/A')} mins` | **Rating:** `★ {details.get('rating')}` ({details.get('vote_count', 0):,} votes)"
                        )
                        st.write(details.get("overview", "No synopsis available."))
                        st.markdown(f"**🎬 Director:** {details.get('director', 'Unknown')} | **🌟 Cast:** {', '.join(details.get('cast', [])[:4])}")
        else:
            st.info("No movies matched your exact filter combination. Try expanding the year range or lowering the minimum rating.")
