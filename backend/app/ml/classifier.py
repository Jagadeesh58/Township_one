"""
Township One - Residential Complaint Classifier Service.

Provides category and urgency prediction with:
- Local primary/fallback scikit-learn Naive Bayes model using TF-IDF word (1-3) and char (3-5) n-grams.
- Cloud Groq API integration with 5s timeout, 1 retry, and 429 backoff sending ONLY complaint text.
- Fallback mechanism to local model on Groq absence or error.
- Low-confidence and empty input gating to UNCLASSIFIED / human review.
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

VALID_CATEGORIES = [
    "PLUMBING", "ELECTRICAL", "LIFT", "CLEANLINESS",
    "WATER_SUPPLY", "SECURITY", "COMMON_AREA", "GENERAL"
]

VALID_URGENCIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

MODEL_VERSION = "v1-nb"
DEFAULT_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "complaints_v1.csv")
DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "data", "classifier_model.joblib")

# In-memory cached model artifacts
_LOADED_MODELS: Optional[Tuple[Pipeline, Pipeline]] = None


def build_pipeline() -> Pipeline:
    """Constructs scikit-learn feature union and multinomial naive bayes pipeline."""
    features = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 3), analyzer="word", min_df=1)),
        ("char", TfidfVectorizer(ngram_range=(3, 5), analyzer="char_wb", min_df=1)),
    ])
    return Pipeline([
        ("features", features),
        ("clf", MultinomialNB(alpha=0.1)),
    ])


def train_model(
    csv_path: Optional[str] = None,
    save_path: Optional[str] = None
) -> Tuple[Pipeline, Pipeline]:
    """Trains category and urgency pipelines from complaints dataset and persists artifacts."""
    csv_file = csv_path or DEFAULT_DATA_PATH
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Training dataset not found at {csv_file}")

    df = pd.read_csv(csv_file)
    X = df["text"].astype(str).tolist()
    y_cat = df["category"].astype(str).tolist()
    y_urg = df["urgency"].astype(str).tolist()

    cat_pipeline = build_pipeline()
    cat_pipeline.fit(X, y_cat)

    urg_pipeline = build_pipeline()
    urg_pipeline.fit(X, y_urg)

    out_file = save_path or DEFAULT_MODEL_PATH
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    joblib.dump({"category_model": cat_pipeline, "urgency_model": urg_pipeline}, out_file)

    global _LOADED_MODELS
    _LOADED_MODELS = (cat_pipeline, urg_pipeline)
    return cat_pipeline, urg_pipeline


def get_local_models(model_path: Optional[str] = None) -> Tuple[Pipeline, Pipeline]:
    """Retrieves cached pipelines or loads/trains from persistent storage."""
    global _LOADED_MODELS
    if _LOADED_MODELS is not None:
        return _LOADED_MODELS

    path = model_path or DEFAULT_MODEL_PATH
    if os.path.exists(path):
        try:
            bundle = joblib.load(path)
            _LOADED_MODELS = (bundle["category_model"], bundle["urgency_model"])
            return _LOADED_MODELS
        except Exception as e:
            logger.warning("Failed loading serialized model, retraining: %s", e)

    return train_model(save_path=path)


def _call_groq_api(
    text: str,
    api_key: str,
    model_id: str
) -> Optional[Dict[str, Any]]:
    """
    Calls Groq chat completions endpoint with 5s timeout, 1 retry, and 429 backoff.
    Sends strictly the complaint text in resident prompt.
    """
    import httpx

    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a residential maintenance triage assistant for Township One. "
                    "Analyze the complaint text and classify it into exactly one category from: "
                    f"{VALID_CATEGORIES} and one urgency from: {VALID_URGENCIES}. "
                    "Output JSON only: {\"category\": \"...\", \"urgency\": \"...\"}"
                ),
            },
            {
                "role": "user",
                "content": text,  # Strictly sending only complaint text
            },
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }

    max_attempts = 2  # Initial call + 1 retry
    for attempt in range(max_attempts):
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(endpoint, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    cat = parsed.get("category", "").upper()
                    urg = parsed.get("urgency", "").upper()
                    if cat in VALID_CATEGORIES and urg in VALID_URGENCIES:
                        return {"category": cat, "urgency": urg}
                    return None
                elif resp.status_code == 429 and attempt == 0:
                    # 429 rate limit backoff
                    retry_after = float(resp.headers.get("retry-after", "1.5"))
                    time.sleep(retry_after)
                    continue
                else:
                    logger.warning("Groq API returned status %s: %s", resp.status_code, resp.text)
                    if attempt == 0:
                        time.sleep(1.0)
                        continue
                    return None
        except httpx.TimeoutException:
            logger.warning("Groq API timed out after 5s (attempt %d)", attempt + 1)
            if attempt == 0:
                continue
            return None
        except Exception as e:
            logger.warning("Groq API request error (attempt %d): %s", attempt + 1, e)
            if attempt == 0:
                continue
            return None

    return None


def predict_category_and_urgency(
    text: str,
    groq_api_key: Optional[str] = None,
    groq_model_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Predicts category and urgency for resident complaint.
    Attempts Groq call if key is available; falls back cleanly to local model.
    Low-confidence or empty inputs flag human review.
    """
    clean_text = (text or "").strip()
    if len(clean_text) < 3:
        return {
            "category": "UNCLASSIFIED",
            "urgency": "MEDIUM",
            "confidence": 0.0,
            "provider": "local_nb",
            "fallback_used": True,
            "model_version": MODEL_VERSION,
            "needs_human_review": True,
        }

    key = groq_api_key or settings.GROQ_API_KEY
    model_id = groq_model_id or settings.GROQ_MODEL_ID

    # Attempt Groq API invocation if key is provided
    if key and key.strip():
        groq_result = _call_groq_api(clean_text, key.strip(), model_id)
        if groq_result:
            return {
                "category": groq_result["category"],
                "urgency": groq_result["urgency"],
                "confidence": 0.95,
                "provider": "groq",
                "fallback_used": False,
                "model_version": model_id,
                "needs_human_review": False,
            }
        logger.info("Groq API unavailable or returned invalid output; falling back to local model.")

    # Fallback to local Naive Bayes model
    cat_model, urg_model = get_local_models()

    cat_probs = cat_model.predict_proba([clean_text])[0]
    cat_idx = cat_probs.argmax()
    cat_conf = float(cat_probs[cat_idx])
    predicted_category = str(cat_model.classes_[cat_idx])

    urg_probs = urg_model.predict_proba([clean_text])[0]
    urg_idx = urg_probs.argmax()
    urg_conf = float(urg_probs[urg_idx])
    predicted_urgency = str(urg_model.classes_[urg_idx])

    combined_confidence = round(cat_conf * urg_conf, 4)

    # Low confidence threshold triggers human review
    if cat_conf < 0.25 or combined_confidence < 0.05:
        return {
            "category": "UNCLASSIFIED",
            "urgency": predicted_urgency,
            "confidence": round(cat_conf, 4),
            "provider": "local_nb",
            "fallback_used": True,
            "model_version": MODEL_VERSION,
            "needs_human_review": True,
        }

    return {
        "category": predicted_category,
        "urgency": predicted_urgency,
        "confidence": round(cat_conf, 4),
        "provider": "local_nb",
        "fallback_used": True,
        "model_version": MODEL_VERSION,
        "needs_human_review": False,
    }
