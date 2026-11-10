"""
CinePulse - UI Component Library
Provides reusable Netflix-themed Streamlit components:
- load_css: Injects custom styles
- render_navbar: Top navigation bar with original red wordmark and page links
- movie_card: Individual movie card with poster, title, year, rating, and hover zoom
- movie_row: Horizontally scrolling container of movie cards
- render_hero_banner: Featured billboard banner
- SAMPLE_MOVIES: Curated sample data for previewing layouts
"""

from pathlib import Path
import html
import json
import streamlit as st

# Path to the shared styles.css file and local watchlist persistence
CSS_PATH = Path(__file__).parent.parent / "styles.css"
WATCHLIST_FILE = Path(__file__).parent.parent / "watchlist.json"


def load_css(css_file: Path | str = CSS_PATH) -> None:
    """Reads and injects the custom Netflix-style CSS into the Streamlit app."""
    path = Path(css_file)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"Styles file not found at {path}")


def load_watchlist_from_disk() -> dict[int, dict]:
    """Reads saved watchlist from local disk to persist across sessions and page reloads."""
    if WATCHLIST_FILE.exists():
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        except Exception:
            return {}
    return {}


def save_watchlist_to_disk(wl: dict[int, dict]) -> None:
    """Saves current watchlist state to local disk."""
    try:
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in wl.items()}, f, indent=2)
    except Exception:
        pass


def init_watchlist() -> dict[int, dict]:
    """
    Initializes and retrieves the user's watchlist dictionary in session state.
    Loads existing saved state from disk (or starts clean and empty).
    No movies are forced or reinjected by default.
    """
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = load_watchlist_from_disk()
    return st.session_state["watchlist"]


def handle_watchlist_action() -> None:
    """
    Intercepts ?toggle_watchlist=<id> query parameters from movie card buttons,
    adds/removes the movie from st.session_state['watchlist'], saves to disk, displays
    an instant notification, clears the query parameter, and refreshes the page.
    """
    init_watchlist()
    if "toggle_watchlist" in st.query_params:
        try:
            m_id = int(st.query_params["toggle_watchlist"])
            wl = st.session_state["watchlist"]
            if m_id in wl:
                removed_title = wl[m_id].get("title", "Movie")
                del wl[m_id]
                save_watchlist_to_disk(wl)
                st.toast(f"Removed '{removed_title}' from Watchlist", icon="🗑️")
            else:
                from utils.tmdb_client import get_movie_details
                details = get_movie_details(m_id)
                if details:
                    wl[m_id] = details
                    save_watchlist_to_disk(wl)
                    st.toast(f"Added '{details['title']}' to Watchlist!", icon="🔖")
            st.query_params.clear()
            st.rerun()
        except Exception:
            st.query_params.clear()


def render_navbar(active_page: str = "Home") -> None:
    """
    Renders the top navigation bar with:
    - Original brand wordmark 'CINEPULSE' in bold Netflix red
    - Direct navigation links to all pages (Home, Trending, Search, Recommendations, Watchlist)
    - Live Watchlist counter badge
    """
    handle_watchlist_action()
    wl = init_watchlist()
    wl_count = len(wl)

    pages = [
        {"name": "Home", "href": "/"},
        {"name": "Trending", "href": "/Trending"},
        {"name": "Search", "href": "/Search"},
        {"name": "Recommendations", "href": "/Recommendations"},
        {"name": f"Watchlist ({wl_count})", "href": "/Watchlist"},
    ]

    links_html = "".join(
        [
            f'<a href="{p["href"]}" target="_self" class="navbar-nav-link {"active" if p["name"].startswith(active_page) else ""}">{p["name"]}</a>'
            for p in pages
        ]
    )

    navbar_html = f"""
    <header class="cinepulse-navbar">
        <div class="navbar-brand-section">
            <a href="/" target="_self" class="brand-wordmark">
                CINEPULSE<span class="accent-dot"></span>
            </a>
            <nav class="navbar-nav-links">
                {links_html}
            </nav>
        </div>
        <div class="navbar-badge">
            TMDB Powered
        </div>
    </header>
    """
    st.markdown(navbar_html, unsafe_allow_html=True)


FALLBACK_POSTER = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&auto=format&fit=crop&q=60"


def movie_card(movie: dict, render: bool = False) -> str:
    """
    Generates a single movie card component with poster, title, year, rating,
    and a Netflix-style bottom-left '+' icon that toggles to '✔' when saved to Watchlist.
    """
    movie_id = movie.get("id") or abs(hash(str(movie.get("title", "")))) % 1000000
    title = html.escape(str(movie.get("title", "Untitled")))
    year = html.escape(str(movie.get("year", "N/A")))
    rating = movie.get("rating", "N/A")
    poster = movie.get("poster") or FALLBACK_POSTER
    tag = movie.get("tag", "")

    # Check Watchlist Status
    wl = init_watchlist()
    is_in_wl = movie_id in wl
    wl_icon = "✔" if is_in_wl else "➕"
    wl_class = "active" if is_in_wl else ""
    wl_tooltip = "In Watchlist (Click to remove)" if is_in_wl else "Add to Watchlist"

    # Rating badge
    rating_display = f"★ {rating}" if rating != "N/A" else ""
    badge_html = f'<div class="movie-rating-badge">{rating_display}</div>' if rating_display else ""
    tag_html = f'<span class="movie-card-tag">{html.escape(tag)}</span>' if tag else ""

    card_html = (
        f'<div class="movie-card" title="{title} ({year})">'
        f'<div class="poster-wrapper">'
        f'<img src="{poster}" alt="{title}" class="movie-poster-img" loading="lazy" onerror="this.src=\'{FALLBACK_POSTER}\';" />'
        f'{badge_html}'
        f'<a href="?toggle_watchlist={movie_id}" target="_self" class="watchlist-card-btn {wl_class}" title="{wl_tooltip}">'
        f'{wl_icon}'
        f'</a>'
        f'</div>'
        f'<div class="movie-card-info">'
        f'<h4 class="movie-card-title">{title}</h4>'
        f'<div class="movie-card-meta">'
        f'<span class="movie-card-year">{year}</span>'
        f'{tag_html}'
        f'</div>'
        f'</div>'
        f'</div>'
    )

    if render:
        st.markdown(card_html, unsafe_allow_html=True)

    return card_html


def movie_row(title: str, movies: list[dict], see_all_link: str | None = None) -> None:
    """
    Renders a section title and a horizontally scrolling row of movie cards.
    Guarantees horizontal layout via inline/dedented HTML to prevent vertical stacking.
    """
    cards_html = "".join([movie_card(m) for m in movies])
    see_all_html = (
        f'<a href="{see_all_link}" target="_self" class="row-see-all">See All ›</a>'
        if see_all_link
        else ""
    )
    title_escaped = html.escape(title)

    row_html = (
        f'<section class="movie-section">'
        f'<div class="movie-section-header">'
        f'<h3 class="row-title">{title_escaped}</h3>'
        f'{see_all_html}'
        f'</div>'
        f'<div class="movie-row-scroller">'
        f'{cards_html}'
        f'</div>'
        f'</section>'
    )
    st.markdown(row_html, unsafe_allow_html=True)


def render_hero_banner(featured_movie: dict | None = None) -> None:
    """
    Renders a Netflix-style billboard banner featuring a highlight movie.
    """
    if featured_movie is None:
        featured_movie = {
            "title": "Dune: Part Two",
            "year": "2024",
            "rating": "8.5",
            "genre": "Sci-Fi • Adventure",
            "backdrop": "https://image.tmdb.org/t/p/original/xJHokMbljvjADYdit5fK5VQsXEG.jpg",
            "overview": (
                "Paul Atreides unites with Chani and the Fremen while seeking revenge "
                "against the conspirators who destroyed his family. Facing a choice between "
                "the love of his life and the fate of the universe, he endeavors to prevent a terrible future."
            ),
        }

    title = html.escape(str(featured_movie.get("title", "")))
    overview = html.escape(str(featured_movie.get("overview", "")))
    year = html.escape(str(featured_movie.get("year", "")))
    rating = html.escape(str(featured_movie.get("rating", "")))
    genre = html.escape(str(featured_movie.get("genre", "")))
    backdrop = featured_movie.get("backdrop", "")

    hero_html = f"""
    <div class="hero-banner" style="background-image: url('{backdrop}');">
        <div class="hero-overlay"></div>
        <div class="hero-content">
            <span class="hero-badge">Featured Spotlight</span>
            <h1 class="hero-title">{title}</h1>
            <div class="hero-meta">
                <span class="hero-rating">★ {rating} Rating</span>
                <span class="hero-year">{year}</span>
                <span class="hero-genre">{genre}</span>
            </div>
            <p class="hero-overview">{overview}</p>
            <div class="hero-actions">
                <a href="/Recommendations" target="_self" class="hero-btn-play">
                    ▶ Explore Matches
                </a>
                <a href="/Trending" target="_self" class="hero-btn-info">
                    ℹ More Details
                </a>
            </div>
        </div>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)


# TMDB Genres mapping
TMDB_GENRES = {
    "Action": 28,
    "Adventure": 12,
    "Animation": 16,
    "Comedy": 35,
    "Crime": 80,
    "Documentary": 99,
    "Drama": 18,
    "Family": 10751,
    "Fantasy": 14,
    "History": 36,
    "Horror": 27,
    "Music": 10402,
    "Mystery": 9648,
    "Romance": 10749,
    "Sci-Fi": 878,
    "Thriller": 53,
    "War": 10752,
    "Western": 37,
}

LANGUAGE_OPTIONS = {
    "All Languages": "all",
    "English": "en",
    "Korean": "ko",
    "Japanese": "ja",
    "Spanish": "es",
    "French": "fr",
    "Italian": "it",
    "German": "de",
    "Hindi": "hi",
}

RUNTIME_BRACKETS = {
    "Any Runtime": None,
    "Under 90 mins (< 90m)": (0, 89),
    "Standard (90 – 120 mins)": (90, 120),
    "Feature (120 – 150 mins)": (120, 150),
    "Epic (150+ mins)": (150, 400),
}


def render_filter_console(key_prefix: str = "home") -> list[dict] | None:
    """
    Renders the rectangular filter console implementing all 5 core assignment filters:
    1. Year/Decade ranges (From Year & To Year text inputs)
    2. Minimum ratings score slider & vote count requirements
    3. Personnel: Actor or Director name search
    4. Genre combinations with logical operators (AND / OR)
    5. Content specifications:
       - Runtime brackets (< 90m, 90-120m, 120-150m, 150m+)
       - US Certification levels (All, G, PG, PG-13, R, NC-17)
       - Original language filter (English, Korean, Japanese, Spanish, etc.)

    Returns:
        List of filtered movie dictionaries if filter is active, otherwise None.
    """
    from utils.tmdb_client import discover_movies, search_person

    state_key = f"{key_prefix}_filter_results"
    active_key = f"{key_prefix}_filter_active"

    st.markdown(
        """
        <div class="filter-console-wrapper">
            <div class="filter-console-header">
                <h3 class="filter-console-title">🎛️ Advanced Movie Discovery & Filters</h3>
                <span class="filter-console-tag">Core Filters</span>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # Row 1: Genres (with AND/OR logic) & Year Range
    c_genres, c_logic, c_yr_from, c_yr_to = st.columns([3, 1.8, 1.1, 1.1])
    with c_genres:
        sel_genres = st.multiselect(
            "Select Genres",
            options=list(TMDB_GENRES.keys()),
            default=[],
            key=f"{key_prefix}_genres",
            placeholder="e.g. Action, Sci-Fi...",
        )
    with c_logic:
        logic_op = st.radio(
            "Genre Logic",
            options=["OR (Match Any)", "AND (Match All)"],
            horizontal=True,
            key=f"{key_prefix}_logic",
        )
    with c_yr_from:
        year_from_str = st.text_input("From Year", value="1990", key=f"{key_prefix}_yr_from")
    with c_yr_to:
        year_to_str = st.text_input("To Year", value="2026", key=f"{key_prefix}_yr_to")

    # Row 2: Quality Thresholds (Rating & Votes) & Personnel (Actor/Director)
    c_rating, c_votes, c_person = st.columns([2.5, 2, 2.5])
    with c_rating:
        min_rating = st.slider(
            "Minimum TMDB Rating",
            min_value=0.0,
            max_value=10.0,
            value=7.0,
            step=0.1,
            key=f"{key_prefix}_rating",
        )
    with c_votes:
        min_votes = st.select_slider(
            "Minimum Vote Count",
            options=[10, 50, 100, 250, 500, 1000, 2500],
            value=100,
            key=f"{key_prefix}_votes",
        )
    with c_person:
        person_query = st.text_input(
            "Personnel (Actor or Director)",
            placeholder="e.g. Christopher Nolan, Leonardo DiCaprio",
            key=f"{key_prefix}_person",
        )

    # Row 3: Content Specifications (Runtime, Certification, Language)
    c_runtime, c_cert, c_lang = st.columns([2.5, 2, 2.5])
    with c_runtime:
        runtime_sel = st.selectbox(
            "Runtime Bracket",
            options=list(RUNTIME_BRACKETS.keys()),
            index=0,
            key=f"{key_prefix}_runtime",
        )
    with c_cert:
        cert_sel = st.selectbox(
            "US Certification",
            options=["All", "G", "PG", "PG-13", "R", "NC-17"],
            index=0,
            key=f"{key_prefix}_cert",
        )
    with c_lang:
        lang_sel = st.selectbox(
            "Original Language",
            options=list(LANGUAGE_OPTIONS.keys()),
            index=0,
            key=f"{key_prefix}_lang",
        )

    # Row 4: Action Buttons
    c_apply, c_reset, _ = st.columns([1.5, 1.2, 5])
    with c_apply:
        apply_clicked = st.button("🔴 Apply Filters", type="primary", use_container_width=True, key=f"{key_prefix}_apply")
    with c_reset:
        reset_clicked = st.button("🔄 Reset", use_container_width=True, key=f"{key_prefix}_reset")

    st.markdown("</div>", unsafe_allow_html=True)

    if reset_clicked:
        st.session_state[state_key] = None
        st.session_state[active_key] = False
        st.rerun()

    if apply_clicked:
        # 1. Parse Years
        try:
            start_yr = int(year_from_str.strip())
        except ValueError:
            start_yr = 1900
        try:
            end_yr = int(year_to_str.strip())
        except ValueError:
            end_yr = 2030

        # 2. Parse Genres & Operator
        genre_ids = [TMDB_GENRES[g] for g in sel_genres if g in TMDB_GENRES]
        genre_operator = "AND" if "AND" in logic_op else "OR"

        # 3. Parse Personnel ID
        person_id = None
        if person_query.strip():
            with st.spinner(f"Looking up '{person_query}'..."):
                person_id = search_person(person_query.strip())
                if not person_id:
                    st.warning(f"Could not find person named '{person_query}'. Proceeding without personnel filter.")

        # 4. Parse Runtime & Language
        runtime_range = RUNTIME_BRACKETS.get(runtime_sel)
        orig_lang = LANGUAGE_OPTIONS.get(lang_sel, "all")

        # 5. Query TMDB Discover
        with st.spinner("Finding matching movies..."):
            results = discover_movies(
                year_range=(start_yr, end_yr),
                min_rating=min_rating,
                min_vote_count=min_votes,
                with_genres=genre_ids if genre_ids else None,
                genre_operator=genre_operator,
                runtime_range=runtime_range,
                certification=cert_sel,
                person_id=person_id,
                original_language=orig_lang,
            )
            st.session_state[state_key] = results
            st.session_state[active_key] = True

    if st.session_state.get(active_key):
        return st.session_state.get(state_key, [])

    return None


def render_placeholder_page(
    page_title: str,
    feature_description: str,
    active_nav: str,
    icon: str = "🎬",
) -> None:
    """
    Standard placeholder renderer for future feature pages.
    Displays page title, consistent navbar, and 'Coming soon' banner.
    """
    load_css()
    render_navbar(active_page=active_nav)

    st.markdown(
        f"""
        <div class="coming-soon-container">
            <div class="coming-soon-icon">{icon}</div>
            <h1 class="coming-soon-title">{html.escape(page_title)}</h1>
            <p class="coming-soon-text">{html.escape(feature_description)}</p>
            <span class="coming-soon-badge">Feature Coming Soon</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Curated hardcoded sample movies for template visual testing
SAMPLE_TRENDING_MOVIES = [
    {
        "title": "Dune: Part Two",
        "year": "2024",
        "rating": 8.5,
        "poster": "https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg",
        "tag": "98% Match",
    },
    {
        "title": "Oppenheimer",
        "year": "2023",
        "rating": 8.1,
        "poster": "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg",
        "tag": "95% Match",
    },
    {
        "title": "Across the Spider-Verse",
        "year": "2023",
        "rating": 8.4,
        "poster": "https://image.tmdb.org/t/p/w500/8Vt6mWEReuy4Of61Lnj5Xj704m8.jpg",
        "tag": "99% Match",
    },
    {
        "title": "Interstellar",
        "year": "2014",
        "rating": 8.4,
        "poster": "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
        "tag": "97% Match",
    },
    {
        "title": "Inception",
        "year": "2010",
        "rating": 8.4,
        "poster": "https://image.tmdb.org/t/p/w500/edv5CZvWj09upOsy2Y6IwDhK8bt.jpg",
        "tag": "96% Match",
    },
    {
        "title": "The Dark Knight",
        "year": "2008",
        "rating": 8.5,
        "poster": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
        "tag": "98% Match",
    },
    {
        "title": "Parasite",
        "year": "2019",
        "rating": 8.5,
        "poster": "https://image.tmdb.org/t/p/w500/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg",
        "tag": "94% Match",
    },
]

SAMPLE_TOP_RATED_MOVIES = [
    {
        "title": "The Godfather",
        "year": "1972",
        "rating": 8.7,
        "poster": "https://image.tmdb.org/t/p/w500/3bhkrj58Vtu7enYsRolD1fZdja1.jpg",
        "tag": "All-Time Best",
    },
    {
        "title": "Pulp Fiction",
        "year": "1994",
        "rating": 8.5,
        "poster": "https://image.tmdb.org/t/p/w500/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg",
        "tag": "Cult Classic",
    },
    {
        "title": "Spirited Away",
        "year": "2001",
        "rating": 8.5,
        "poster": "https://image.tmdb.org/t/p/w500/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg",
        "tag": "Masterpiece",
    },
    {
        "title": "Whiplash",
        "year": "2014",
        "rating": 8.4,
        "poster": "https://image.tmdb.org/t/p/w500/7fn624j5lj3xTme2SgiLCeuedmO.jpg",
        "tag": "Top Rated",
    },
    {
        "title": "The Matrix",
        "year": "1999",
        "rating": 8.2,
        "poster": "https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg",
        "tag": "Iconic",
    },
    {
        "title": "Blade Runner 2049",
        "year": "2017",
        "rating": 8.0,
        "poster": "https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg",
        "tag": "Sci-Fi Peak",
    },
]

SAMPLE_RECOMMENDED_MOVIES = [
    {
        "title": "Fight Club",
        "year": "1999",
        "rating": 8.4,
        "poster": "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        "tag": "96% Match",
    },
    {
        "title": "GoodFellas",
        "year": "1990",
        "rating": 8.5,
        "poster": "https://image.tmdb.org/t/p/w500/aKuFiU82s5ISJpGZp7YkIr3kCUd.jpg",
        "tag": "94% Match",
    },
    {
        "title": "Gladiator",
        "year": "2000",
        "rating": 8.2,
        "poster": "https://image.tmdb.org/t/p/w500/ty8TGRuvJLPUmAR1H1nRIsgwvim.jpg",
        "tag": "91% Match",
    },
    {
        "title": "Arrival",
        "year": "2016",
        "rating": 7.9,
        "poster": "https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg",
        "tag": "93% Match",
    },
    {
        "title": "Se7en",
        "year": "1995",
        "rating": 8.4,
        "poster": "https://image.tmdb.org/t/p/w500/6yoghtyTpznpBik8EngEmJskVUO.jpg",
        "tag": "95% Match",
    },
]
