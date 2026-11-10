"""
Recommendation Engine Module
----------------------------
Implements multiple recommendation algorithms for CinePulse:
1. Content-Based Filtering: Matches structured attributes (genres, cast, director, keywords)
2. NLP Plot Description Matching: Uses semantic TF-IDF cosine similarity & tone analysis
3. Hybrid Recommendation: Combines both models into a unified weighted score
4. Explainable AI: Generates human-readable explanations detailing why a movie was recommended
"""

from typing import Any
import streamlit as st
from utils.tmdb_client import (
    get_movie_details,
    _tmdb_get,
    format_movie_data,
    discover_movies,
)
from utils.nlp import (
    compute_plot_similarities,
    extract_shared_keywords,
    detect_dominant_tones,
)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_candidate_pool(seed_movie_id: int, genre_ids: tuple[int, ...] | None = None) -> list[dict[str, Any]]:
    """
    Retrieves a diverse pool of candidate movies from TMDB for the recommendation engine:
    1. Direct TMDB recommendations
    2. Direct TMDB similar titles
    3. Discover titles matching primary genre
    """
    candidates_dict: dict[int, dict[str, Any]] = {}

    # 1. Fetch TMDB Recommendations
    rec_data = _tmdb_get(f"movie/{seed_movie_id}/recommendations")
    if rec_data and "results" in rec_data:
        for m in rec_data["results"]:
            if m.get("id") != seed_movie_id and m.get("poster_path"):
                candidates_dict[m["id"]] = format_movie_data(m)

    # 2. Fetch TMDB Similar titles
    sim_data = _tmdb_get(f"movie/{seed_movie_id}/similar")
    if sim_data and "results" in sim_data:
        for m in sim_data["results"]:
            if m.get("id") != seed_movie_id and m.get("poster_path") and m["id"] not in candidates_dict:
                candidates_dict[m["id"]] = format_movie_data(m)

    # 3. Fallback / Enrichment with same genre if candidate pool is small
    if len(candidates_dict) < 15 and genre_ids:
        disc_movies = discover_movies(with_genres=list(genre_ids[:2]), min_vote_count=200, page=1)
        for m in disc_movies:
            if m.get("id") != seed_movie_id and m["id"] not in candidates_dict:
                candidates_dict[m["id"]] = m

    return list(candidates_dict.values())


def compute_attribute_similarity(seed_details: dict[str, Any], candidate_details: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """
    Computes Content-Based similarity score across structured movie metadata:
    - Director match (weight: 0.35)
    - Cast overlap (weight: 0.25)
    - Genre overlap via Jaccard index (weight: 0.25)
    - Rating quality factor (weight: 0.15)
    """
    shared_factors: dict[str, Any] = {
        "shared_director": None,
        "shared_cast": [],
        "shared_genres": [],
    }

    score = 0.0

    # 1. Director Match
    seed_dir = seed_details.get("director", "Unknown")
    cand_dir = candidate_details.get("director", "Unknown")
    if seed_dir and cand_dir and seed_dir != "Unknown" and seed_dir.lower() == cand_dir.lower():
        score += 0.35
        shared_factors["shared_director"] = seed_dir

    # 2. Cast Overlap
    seed_cast = set(seed_details.get("cast", []))
    cand_cast = set(candidate_details.get("cast", []))
    shared_actors = list(seed_cast.intersection(cand_cast))
    if shared_actors:
        score += min(0.25, len(shared_actors) * 0.12)
        shared_factors["shared_cast"] = shared_actors

    # 3. Genre Overlap
    seed_genres = set(seed_details.get("genres", []))
    cand_genres = set(candidate_details.get("genres", []))
    if seed_genres and cand_genres:
        jaccard = len(seed_genres.intersection(cand_genres)) / len(seed_genres.union(cand_genres))
        score += jaccard * 0.25
        shared_factors["shared_genres"] = list(seed_genres.intersection(cand_genres))
    elif "genre_ids" in candidate_details and "genre_ids" in seed_details:
        seed_g_ids = set(seed_details.get("genre_ids", []))
        cand_g_ids = set(candidate_details.get("genre_ids", []))
        if seed_g_ids and cand_g_ids:
            jaccard = len(seed_g_ids.intersection(cand_g_ids)) / len(seed_g_ids.union(cand_g_ids))
            score += jaccard * 0.25

    # 4. Rating Quality Factor
    cand_rating = float(candidate_details.get("rating", 0.0))
    if cand_rating >= 7.5:
        score += 0.15
    elif cand_rating >= 6.5:
        score += 0.08

    return min(1.0, score), shared_factors


def generate_recommendations(
    seed_movie_id: int,
    strategy: str = "hybrid",  # "hybrid", "nlp", or "content"
    top_n: int = 8,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """
    Main recommendation engine pipeline:
    1. Fetches seed movie deep metadata (overview, director, cast, genres).
    2. Gathers candidate movie pool.
    3. Runs chosen recommendation algorithm:
       - 'nlp': NLP Plot TF-IDF Cosine Similarity & thematic keyword analysis
       - 'content': Content-Based attribute similarity (director, cast, genres)
       - 'hybrid': Weighted combination (50% NLP + 50% Content)
    4. Generates explainable rationale for every recommended movie.

    Returns:
        (seed_movie_details, list_of_recommended_movies_with_explanations)
    """
    seed = get_movie_details(seed_movie_id)
    if not seed:
        return None, []

    seed_genre_ids = tuple(seed.get("genre_ids", []))
    candidates = fetch_candidate_pool(seed_movie_id, seed_genre_ids)
    if not candidates:
        return seed, []

    # Extract plot descriptions for NLP pipeline
    candidate_plots = [c.get("overview", "") for c in candidates]
    seed_plot = seed.get("overview", "")

    # Run NLP Plot Similarity Model (Fast vectorized Cosine Similarity)
    nlp_scores = compute_plot_similarities(seed_plot, candidate_plots)
    seed_tones = detect_dominant_tones(seed_plot)

    # Initial scoring pass across all candidates (fast)
    preliminary_scored = []
    for i, candidate in enumerate(candidates):
        nlp_score = nlp_scores[i]
        # Lightweight genre overlap check
        seed_g = set(seed_genre_ids)
        cand_g = set(candidate.get("genre_ids", []))
        genre_overlap = len(seed_g.intersection(cand_g)) / max(1, len(seed_g.union(cand_g)))

        rough_score = (nlp_score * 0.6) + (genre_overlap * 0.4)
        preliminary_scored.append((rough_score, i, candidate, nlp_score))

    # Sort and pick top candidates to enrich with deep details
    preliminary_scored.sort(key=lambda x: x[0], reverse=True)
    top_candidates = preliminary_scored[:min(top_n + 6, len(preliminary_scored))]

    final_results = []

    for _, i, candidate, nlp_score in top_candidates:
        # Fetch deep details for top candidates
        cand_details = get_movie_details(candidate["id"]) or candidate
        attr_score, shared_factors = compute_attribute_similarity(seed, cand_details)

        # Apply user's selected strategy
        if strategy == "nlp":
            raw_score = (nlp_score * 0.85) + (attr_score * 0.15)
        elif strategy == "content":
            raw_score = (attr_score * 0.85) + (nlp_score * 0.15)
        else:  # hybrid (recommended)
            raw_score = (nlp_score * 0.50) + (attr_score * 0.50)

        # Scale percentage match (typically 65% - 98%)
        scaled_pct = int(round(65 + (raw_score * 33)))
        scaled_pct = max(60, min(98, scaled_pct))

        # Extract shared keywords between plots for transparent explanation
        shared_keywords = extract_shared_keywords(seed_plot, candidate.get("overview", ""), top_k=4)
        cand_tones = detect_dominant_tones(candidate.get("overview", ""))
        shared_tones = list(set(seed_tones).intersection(set(cand_tones)))

        # Generate Human-Readable Explanations
        explanation_points = []
        if shared_factors.get("shared_director"):
            explanation_points.append(f"🎬 **Creative Vision**: Both directed by **{shared_factors['shared_director']}**.")
        if shared_factors.get("shared_cast"):
            actors = ", ".join(shared_factors["shared_cast"][:2])
            explanation_points.append(f"🌟 **Shared Cast**: Features **{actors}**.")
        if shared_factors.get("shared_genres"):
            genres = " & ".join(shared_factors["shared_genres"][:2])
            explanation_points.append(f"🎭 **Genre Synergy**: Shares {genres}.")
        if shared_keywords:
            kw_str = ", ".join(f"#{k}" for k in shared_keywords[:3])
            explanation_points.append(f"🧠 **Plot Overlap**: Common story concepts: *{kw_str}*.")
        if shared_tones:
            explanation_points.append(f"🎭 **Tone & Mood**: Shares a *{shared_tones[0]}* atmosphere.")

        if not explanation_points:
            explanation_points.append("💡 **Thematic Resonance**: High semantic overlap in narrative structure and tone.")

        candidate_result = dict(cand_details)
        candidate_result["match_percentage"] = scaled_pct
        candidate_result["final_score"] = raw_score
        candidate_result["nlp_score"] = round(nlp_score * 100, 1)
        candidate_result["attr_score"] = round(attr_score * 100, 1)
        candidate_result["explanation_points"] = explanation_points
        candidate_result["shared_keywords"] = shared_keywords

        final_results.append(candidate_result)

    final_results.sort(key=lambda x: x["match_percentage"], reverse=True)
    return seed, final_results[:top_n]
