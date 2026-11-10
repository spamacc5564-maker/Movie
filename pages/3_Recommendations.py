"""
Personalized Recommendations & Similar Movie Discovery
------------------------------------------------------
Implements multiple recommendation approaches with transparent explanations:
1. Content-based filtering using structured movie attributes (director, cast, genres)
2. NLP-based matching using TF-IDF analysis of plot descriptions and thematic tone
3. Hybrid blend combining both models
4. Transparent explanations detailing why each title was recommended
"""

import html
import streamlit as st
from utils.ui import load_css, render_navbar
from utils.tmdb_client import search_movies, get_movie_details
from utils.recommender import generate_recommendations

st.set_page_config(
    page_title="Recommendations | CinePulse",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Load styling & navbar
load_css()
render_navbar(active_page="Recommendations")

# Page Header
st.markdown(
    """
    <div style="margin-bottom: 1.5rem;">
        <h1 style="font-size: 2.1rem; font-weight: 800; margin-bottom: 0.2rem;">🎯 Similar Movie Discovery</h1>
        <p style="color: #B3B3B3; font-size: 0.95rem; margin: 0;">
            Find films with similar story arcs, themes, creative direction, and tone — backed by transparent similarity explanations.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Quick picks for iconic seed movies
QUICK_PICKS = [
    {"title": "Inception", "id": 27205, "year": "2010"},
    {"title": "Interstellar", "id": 157336, "year": "2014"},
    {"title": "The Dark Knight", "id": 155, "year": "2008"},
    {"title": "The Matrix", "id": 603, "year": "1999"},
    {"title": "Parasite", "id": 496243, "year": "2019"},
    {"title": "Dune: Part Two", "id": 693134, "year": "2024"},
]

# Session state initialization for seed movie
if "rec_seed_id" not in st.session_state:
    st.session_state["rec_seed_id"] = 27205  # Default: Inception

# -----------------------------------------------------------------------------
# STEP 1: CHOOSE A SEED MOVIE
# -----------------------------------------------------------------------------
st.markdown("### 1️⃣ Choose a Seed Movie")

# Quick-pick button row
qp_cols = st.columns(len(QUICK_PICKS))
for i, qp in enumerate(QUICK_PICKS):
    if qp_cols[i].button(f"{qp['title']}", key=f"qp_{qp['id']}", use_container_width=True):
        st.session_state["rec_seed_id"] = qp["id"]
        st.rerun()

# Or search custom movie
with st.expander("🔎 Or search for any other movie on TMDB...", expanded=False):
    custom_search = st.text_input("Enter movie title to search:", placeholder="e.g. Oppenheimer, Fight Club, Pulp Fiction...")
    if custom_search.strip():
        search_res = search_movies(custom_search.strip())
        if search_res:
            res_options = {f"{m['title']} ({m['year']})": m["id"] for m in search_res[:8]}
            chosen_title = st.selectbox("Select match:", list(res_options.keys()))
            if st.button("Set as Seed Movie"):
                st.session_state["rec_seed_id"] = res_options[chosen_title]
                st.rerun()

# Fetch and display Seed Movie Spotlight
seed_details = get_movie_details(st.session_state["rec_seed_id"])

if seed_details:
    st.markdown(
        f"""
        <div style="background:#1b1b1b; border:1px solid #333; border-radius:8px; padding:1.2rem; margin:1rem 0 1.5rem 0; display:flex; gap:20px; align-items:flex-start;">
            <img src="{seed_details['poster']}" style="width:110px; border-radius:6px;" />
            <div>
                <span style="background:#E50914; color:#fff; font-size:0.75rem; font-weight:800; padding:2px 8px; border-radius:3px; text-transform:uppercase;">Seed Movie Selected</span>
                <h2 style="font-size:1.6rem; margin:6px 0 4px 0; font-weight:800; color:#fff;">{seed_details['title']} <span style="color:#888; font-size:1.2rem;">({seed_details['year']})</span></h2>
                <p style="color:#B3B3B3; font-size:0.88rem; margin:0 0 6px 0;">
                    <strong>Director:</strong> {seed_details.get('director', 'Unknown')} &nbsp;|&nbsp; 
                    <strong>Genres:</strong> {seed_details.get('genre_str', 'General')} &nbsp;|&nbsp; 
                    <strong>Rating:</strong> ★ {seed_details.get('rating')}
                </p>
                <p style="color:#d4d4d4; font-size:0.86rem; line-height:1.4; margin:0;">{seed_details.get('overview', '')[:260]}...</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# STEP 2: CHOOSE RECOMMENDATION STRATEGY
# -----------------------------------------------------------------------------
st.markdown("### 2️⃣ Select Recommendation Algorithm")

col_strat, col_topn = st.columns([3, 1])

with col_strat:
    strategy_choice = st.radio(
        "Recommendation Approach (Minimum 2 Required by Assignment)",
        options=[
            "⚡ Hybrid Blend (NLP Plot + Metadata) — Recommended",
            "🧠 NLP Plot Similarity (TF-IDF Vectorization & Tone Analysis)",
            "🎭 Content-Based (Cast, Director & Genre Attributes)",
        ],
        index=0,
    )

with col_topn:
    top_n = st.slider("Number of Recommendations", min_value=3, max_value=12, value=6, step=1)

# Map human choice to algorithm key
if "Hybrid" in strategy_choice:
    strategy_key = "hybrid"
elif "NLP" in strategy_choice:
    strategy_key = "nlp"
else:
    strategy_key = "content"

# -----------------------------------------------------------------------------
# STEP 3: RUN RECOMMENDATION ENGINE & DISPLAY WITH EXPLANATIONS
# -----------------------------------------------------------------------------
btn_generate = st.button("🔴 Discover Similar Movies", type="primary", use_container_width=False)

# Trigger or use cached recommendations in session state
rec_state_key = f"recs_{st.session_state['rec_seed_id']}_{strategy_key}_{top_n}"

if btn_generate or rec_state_key in st.session_state:
    if btn_generate:
        with st.spinner("Analyzing plot descriptions, extracting TF-IDF features, and computing similarity..."):
            _, recommendations = generate_recommendations(
                seed_movie_id=st.session_state["rec_seed_id"],
                strategy=strategy_key,
                top_n=top_n,
            )
            st.session_state[rec_state_key] = recommendations
    else:
        recommendations = st.session_state[rec_state_key]

    if not recommendations:
        st.info("No candidates found with sufficient similarity. Try selecting a different seed movie.")
    else:
        st.markdown(f"### 🎬 Top Matches for fans of *{seed_details['title']}*")
        st.caption(f"Ranked using **{strategy_choice.split('—')[0].strip()}** model.")

        for movie in recommendations:
            title = html.escape(str(movie.get("title", "Untitled")))
            year = html.escape(str(movie.get("year", "N/A")))
            rating = movie.get("rating", "N/A")
            cert = movie.get("certification", "NR")
            runtime = f"{movie.get('runtime')} mins" if movie.get("runtime") else "N/A"
            genres_str = movie.get("genre_str", "General")
            pct = movie.get("match_percentage", 80)
            overview = html.escape(str(movie.get("overview", "No synopsis available.")))

            # Format bullet points
            bullet_html = "".join(
                [f'<div class="rec-explanation-item">• {pt}</div>' for pt in movie.get("explanation_points", [])]
            )

            # Card container
            card_html = (
                f'<div class="rec-card-container">'
                f'<div class="rec-card-poster">'
                f'<img src="{movie["poster"]}" alt="{title}" loading="lazy" />'
                f'<div class="rec-match-badge">{pct}% Match</div>'
                f'</div>'
                f'<div class="rec-card-content">'
                f'<h3 class="rec-card-title">{title} <span style="color:#888; font-size:1rem; font-weight:400;">({year})</span></h3>'
                f'<div class="rec-card-meta">'
                f'<span style="background:#222; border:1px solid #444; padding:1px 6px; border-radius:3px; font-weight:700;">{cert}</span>'
                f'<span>⏱️ {runtime}</span>'
                f'<span>🎭 {genres_str}</span>'
                f'<span style="color:#46D369; font-weight:700;">★ {rating}</span>'
                f'</div>'
                f'<div class="rec-explanation-box">'
                f'<div class="rec-explanation-title">💡 Why this was recommended</div>'
                f'{bullet_html}'
                f'</div>'
                f'<p style="color:#bbb; font-size:0.85rem; line-height:1.4; margin:6px 0 0 0;">{overview}</p>'
                f'</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # STEP 4: SIDE-BY-SIDE FEATURE COMPARISON
        # ---------------------------------------------------------------------
        st.markdown("---")
        with st.expander("⚖️ Side-by-Side Feature Comparison: Seed vs Recommended Movie", expanded=False):
            rec_titles = [f"{m['title']} ({m['year']}) - {m['match_percentage']}% Match" for m in recommendations]
            comp_idx = st.selectbox("Select recommended movie to compare against seed:", range(len(recommendations)), format_func=lambda i: rec_titles[i])
            comp_movie = recommendations[comp_idx]

            col_seed, col_rec = st.columns(2)
            with col_seed:
                st.markdown(f"#### 🎬 Seed: **{seed_details['title']}**")
                st.image(seed_details["poster"], width=140)
                st.markdown(f"- **Director:** {seed_details.get('director', 'Unknown')}")
                st.markdown(f"- **Top Cast:** {', '.join(seed_details.get('cast', [])[:3])}")
                st.markdown(f"- **Genres:** {seed_details.get('genre_str', 'N/A')}")
                st.markdown(f"- **Runtime:** {seed_details.get('runtime', 'N/A')} mins")
                st.markdown(f"- **US Rating:** {seed_details.get('certification', 'NR')}")
                st.markdown(f"- **TMDB Score:** ★ {seed_details.get('rating')}")

            with col_rec:
                st.markdown(f"#### 🎯 Recommended: **{comp_movie['title']}** ({comp_movie['match_percentage']}% Match)")
                st.image(comp_movie["poster"], width=140)
                st.markdown(f"- **Director:** {comp_movie.get('director', 'Unknown')}")
                st.markdown(f"- **Top Cast:** {', '.join(comp_movie.get('cast', [])[:3])}")
                st.markdown(f"- **Genres:** {comp_movie.get('genre_str', 'N/A')}")
                st.markdown(f"- **Runtime:** {comp_movie.get('runtime', 'N/A')} mins")
                st.markdown(f"- **US Rating:** {comp_movie.get('certification', 'NR')}")
                st.markdown(f"- **TMDB Score:** ★ {comp_movie.get('rating')}")
