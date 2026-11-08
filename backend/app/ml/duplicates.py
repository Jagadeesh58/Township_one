"""
Township One - Complaint Duplicate Detection Service.

Identifies potential duplicate tickets from the same tower / time window using
character n-gram TF-IDF cosine similarity. Character n-grams robustly capture
misspellings, compound words, and script variations in multilingual resident text.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _extract_text(complaint: Dict[str, Any]) -> str:
    """Extracts text representation from complaint dictionary."""
    if "text" in complaint and complaint["text"]:
        return str(complaint["text"]).strip()
    title = str(complaint.get("title", "")).strip()
    desc = str(complaint.get("description", "")).strip()
    return f"{title} {desc}".strip()


def find_duplicate_candidates(
    new_text: str,
    existing_complaints: List[Dict[str, Any]],
    threshold: float = 0.45,
    max_candidates: int = 5,
    tower_id: Optional[str] = None,
    time_window_hours: Optional[float] = None,
    reference_time: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Finds existing complaints similar to new_text using char n-gram TF-IDF cosine similarity.
    
    Filters candidates by optional tower and time window if specified, scores candidates,
    filters by similarity >= threshold, and returns top candidates sorted descending.
    """
    clean_new = (new_text or "").strip()
    if not clean_new or not existing_complaints:
        return []

    # Filter by tower if specified and present
    filtered_complaints: List[Dict[str, Any]] = []
    ref_time = reference_time or datetime.now(timezone.utc)

    for item in existing_complaints:
        # Tower isolation filter
        if tower_id is not None and "tower_id" in item and item["tower_id"]:
            if str(item["tower_id"]) != str(tower_id):
                continue

        # Time window filter
        if time_window_hours is not None and "created_at" in item and item["created_at"]:
            item_time = item["created_at"]
            if isinstance(item_time, str):
                try:
                    item_time = datetime.fromisoformat(item_time.replace("Z", "+00:00"))
                except Exception:
                    item_time = None
            if isinstance(item_time, datetime):
                if item_time.tzinfo is None:
                    item_time = item_time.replace(tzinfo=timezone.utc)
                delta_hours = abs((ref_time - item_time).total_seconds()) / 3600.0
                if delta_hours > time_window_hours:
                    continue

        item_text = _extract_text(item)
        if item_text:
            filtered_complaints.append(item)

    if not filtered_complaints:
        return []

    # Build corpus: query text at index 0 followed by candidates
    corpus = [clean_new] + [_extract_text(c) for c in filtered_complaints]

    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=1,
    )
    tfidf_vectors = vectorizer.fit_transform(corpus)

    # Compute cosine similarity between query (row 0) and all candidates (rows 1..)
    query_vec = tfidf_vectors[0:1]
    candidate_vecs = tfidf_vectors[1:]
    similarities = cosine_similarity(query_vec, candidate_vecs).flatten()

    # Pair with complaints, filter above threshold, sort descending
    scored_candidates = []
    for comp, score in zip(filtered_complaints, similarities):
        score_val = float(score)
        if score_val >= threshold:
            candidate_copy = dict(comp)
            candidate_copy["similarity_score"] = round(score_val, 4)
            scored_candidates.append(candidate_copy)

    # Sort descending by similarity score
    scored_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored_candidates[:max_candidates]
