"""
NLP Processing Module
---------------------
Provides natural language processing techniques for content analysis, feature extraction,
and semantic matching of movie plot descriptions:
1. Text cleaning and token normalization
2. TF-IDF feature extraction (scikit-learn) with unigrams & bigrams
3. Cosine similarity computation across plot overviews
4. Shared semantic keyword extraction for human-readable explanations
5. Tone / emotional sentiment polarity analysis
"""

import re
from typing import Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Lexicon for emotional / thematic tone matching
TONE_LEXICON = {
    "Dark & Suspenseful": {"murder", "killer", "investigation", "dark", "death", "mystery", "crime", "detective", "revenge", "danger", "deadly", "conspiracy", "secrets", "threat", "violence"},
    "Mind-Bending & Sci-Fi": {"reality", "dream", "simulation", "memory", "future", "space", "time", "dimension", "artificial", "universe", "alien", "galaxy", "technology", "quantum"},
    "High-Stakes & Action": {"mission", "heist", "battle", "war", "agents", "soldier", "fight", "escape", "survival", "assassin", "chase", "combat", "destruction", "military"},
    "Emotional & Character-Driven": {"family", "love", "friendship", "relationship", "father", "mother", "loss", "grief", "heart", "struggle", "journey", "home", "hope", "growing"},
    "Humorous & Playful": {"funny", "comedy", "hilarious", "misadventure", "accident", "bizarre", "chaos", "crazy", "quirky", "joke", "prank"},
}

# Generic words to exclude from keyword explanations
EXCLUDE_TERMS = {
    "movie", "film", "story", "follows", "must", "find", "life", "new",
    "one", "two", "world", "takes", "soon", "also", "set", "years", "time", "way", "get", "finds",
    "man", "woman", "young", "old", "help", "back", "take", "make", "become", "first"
}


def clean_text(text: str) -> str:
    """Cleans, normalizes, and tokenizes raw plot descriptions."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_plot_similarities(seed_text: str, candidate_texts: list[str]) -> list[float]:
    """
    Computes TF-IDF vector representations and Cosine Similarity
    between a seed movie plot and a list of candidate movie plots.

    Returns:
        List of similarity scores (0.0 to 1.0) corresponding to each candidate.
    """
    if not seed_text or not candidate_texts:
        return [0.0] * len(candidate_texts)

    cleaned_seed = clean_text(seed_text)
    cleaned_candidates = [clean_text(t) for t in candidate_texts]
    corpus = [cleaned_seed] + cleaned_candidates

    # Fit TF-IDF with unigrams and bigrams using built-in english stop words
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=2500,
        sublinear_tf=True,
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
        seed_vector = tfidf_matrix[0:1]
        candidate_vectors = tfidf_matrix[1:]

        # Pairwise cosine similarity against seed vector
        sim_scores = cosine_similarity(seed_vector, candidate_vectors)[0]
        return [float(np.clip(score, 0.0, 1.0)) for score in sim_scores]
    except Exception:
        return [0.0] * len(candidate_texts)


def extract_shared_keywords(seed_text: str, candidate_text: str, top_k: int = 4) -> list[str]:
    """
    Identifies shared meaningful terms between two movie descriptions
    to generate natural-language similarity explanations.
    """
    tokens_a = {w for w in clean_text(seed_text).split() if len(w) > 4 and w not in EXCLUDE_TERMS}
    tokens_b = {w for w in clean_text(candidate_text).split() if len(w) > 4 and w not in EXCLUDE_TERMS}
    shared = list(tokens_a.intersection(tokens_b))
    shared.sort(key=lambda w: len(w), reverse=True)
    return shared[:top_k]


def detect_dominant_tones(plot_text: str) -> list[str]:
    """Detects emotional and thematic tones present in a movie plot."""
    tokens = set(clean_text(plot_text).split())
    matched_tones = []
    for tone_name, keywords in TONE_LEXICON.items():
        if tokens.intersection(keywords):
            matched_tones.append(tone_name)
    return matched_tones if matched_tones else ["General Drama"]
