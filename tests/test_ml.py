"""
Unit tests for Township One Machine Learning and Emergency Services.

Verifies:
- Dataset integrity, balance, and schema compliance in complaints_v1.csv
- Deterministic emergency detector across English, Hindi, and Marathi with conservative negation
- Classifier local Naive Bayes pipeline and Groq fallback mechanism
- Character n-gram TF-IDF duplicate candidate finder
"""

import csv
import os
import unittest
from collections import Counter
from unittest.mock import MagicMock, patch

from backend.app.ml.classifier import (
    DEFAULT_DATA_PATH,
    VALID_CATEGORIES,
    VALID_URGENCIES,
    predict_category_and_urgency,
)
from backend.app.ml.duplicates import find_duplicate_candidates
from backend.app.ml.emergency import detect_emergency


class TestComplaintsDataset(unittest.TestCase):
    """Verifies dataset schema, volume, and class balance requirements."""

    def setUp(self):
        self.assertTrue(os.path.exists(DEFAULT_DATA_PATH), f"Missing dataset at {DEFAULT_DATA_PATH}")
        self.rows = []
        with open(DEFAULT_DATA_PATH, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.fieldnames = list(reader.fieldnames or [])
            self.rows = list(reader)

    def test_minimum_row_count(self):
        """Must contain >= 300 labelled complaints."""
        self.assertGreaterEqual(len(self.rows), 300)

    def test_required_columns(self):
        """Must contain all required column definitions."""
        expected_cols = {"text", "category", "urgency", "language", "incident_family"}
        self.assertTrue(expected_cols.issubset(set(self.fieldnames)))

    def test_categories_valid_and_balanced(self):
        """All 8 categories must be valid and equally represented."""
        cat_counts = Counter(r["category"] for r in self.rows)
        self.assertEqual(set(cat_counts.keys()), set(VALID_CATEGORIES))
        # Each category should have 45 samples
        for cat in VALID_CATEGORIES:
            self.assertEqual(cat_counts[cat], 45)

    def test_urgencies_valid_and_balanced(self):
        """All 4 urgencies must be valid and well-balanced."""
        urg_counts = Counter(r["urgency"] for r in self.rows)
        self.assertEqual(set(urg_counts.keys()), set(VALID_URGENCIES))
        for urg in VALID_URGENCIES:
            self.assertGreaterEqual(urg_counts[urg], 80)
            self.assertLessEqual(urg_counts[urg], 100)

    def test_languages_balanced(self):
        """Must cover English, Hindi, and Marathi evenly."""
        lang_counts = Counter(r["language"] for r in self.rows)
        self.assertEqual(set(lang_counts.keys()), {"en", "hi", "mr"})
        for lang in ["en", "hi", "mr"]:
            self.assertEqual(lang_counts[lang], 120)

    def test_incident_families_count(self):
        """Must contain 40 incident families (5 per category)."""
        families = set(r["incident_family"] for r in self.rows)
        self.assertEqual(len(families), 40)


class TestEmergencyDetection(unittest.TestCase):
    """Verifies deterministic trilingual detection and conservative negation."""

    def test_english_triggers(self):
        fire = detect_emergency("Severe fire breaking out on floor 5 lobby!")
        self.assertTrue(fire["is_emergency"])
        self.assertEqual(fire["trigger"], "FIRE")

        smoke = detect_emergency("Thick black smoke rising from corridor electrical shaft.")
        self.assertTrue(smoke["is_emergency"])
        self.assertEqual(smoke["trigger"], "SMOKE")

        gas = detect_emergency("Heavy gas leak smell coming from kitchen cylinder.")
        self.assertTrue(gas["is_emergency"])
        self.assertEqual(gas["trigger"], "GAS_LEAK")

        lift = detect_emergency("Elevator stuck between floors with children trapped inside!")
        self.assertTrue(lift["is_emergency"])
        self.assertEqual(lift["trigger"], "LIFT_TRAPPED")

        shock = detect_emergency("Electric shock from geyser tap switchboard sparking!")
        self.assertTrue(shock["is_emergency"])
        self.assertEqual(shock["trigger"], "ELECTRIC_SHOCK_SPARKING")

    def test_hindi_devanagari_and_romanized(self):
        # Hindi Devanagari
        res_hi_dev = detect_emergency("आग लग गई है मीटर रूम में जल्दी आओ")
        self.assertTrue(res_hi_dev["is_emergency"])
        self.assertEqual(res_hi_dev["trigger"], "FIRE")
        self.assertEqual(res_hi_dev["language"], "hi")

        res_hi_dev2 = detect_emergency("लिफ्ट अटकी है और लोग अंदर फंसे हैं")
        self.assertTrue(res_hi_dev2["is_emergency"])
        self.assertEqual(res_hi_dev2["trigger"], "LIFT_TRAPPED")
        self.assertEqual(res_hi_dev2["language"], "hi")

        # Hindi Romanized
        res_hi_rom = detect_emergency("switchboard me current laga bahut tej chingari nikli")
        self.assertTrue(res_hi_rom["is_emergency"])
        self.assertEqual(res_hi_rom["trigger"], "ELECTRIC_SHOCK_SPARKING")
        self.assertEqual(res_hi_rom["language"], "hi")

        res_hi_gas = detect_emergency("cylinder se heavy gas leak ho raha hai smell aa rahi hai")
        self.assertTrue(res_hi_gas["is_emergency"])
        self.assertEqual(res_hi_gas["trigger"], "GAS_LEAK")
        self.assertEqual(res_hi_gas["language"], "hi")

    def test_marathi_devanagari_and_romanized(self):
        # Marathi Devanagari
        res_mr_dev = detect_emergency("इमारतीत मोठी आग लागली आहे तातडीने मदत हवी")
        self.assertTrue(res_mr_dev["is_emergency"])
        self.assertEqual(res_mr_dev["trigger"], "FIRE")
        self.assertEqual(res_mr_dev["language"], "mr")

        res_mr_gas = detect_emergency("पाईपलाईनमधून गॅस गळती झाली असून विषारी धूर येत आहे")
        self.assertTrue(res_mr_gas["is_emergency"])
        self.assertIn(res_mr_gas["trigger"], ["GAS_LEAK", "SMOKE"])
        self.assertEqual(res_mr_gas["language"], "mr")

        # Marathi Romanized
        res_mr_rom = detect_emergency("lift madhe lok adakle ahet fan chalat nahi lavkar ya")
        self.assertTrue(res_mr_rom["is_emergency"])
        self.assertEqual(res_mr_rom["trigger"], "LIFT_TRAPPED")
        self.assertEqual(res_mr_rom["language"], "mr")

        res_mr_shock = detect_emergency("bathroom tap la hath lavlyavar current basla ahe")
        self.assertTrue(res_mr_shock["is_emergency"])
        self.assertEqual(res_mr_shock["trigger"], "ELECTRIC_SHOCK_SPARKING")
        self.assertEqual(res_mr_shock["language"], "mr")

    def test_conservative_negation_escalates_on_uncertainty(self):
        """Negation is handled conservatively: escalate when override cues or doubts exist."""
        # Genuine drill without fire
        drill = detect_emergency("routine drill, no smoke")
        self.assertFalse(drill["is_emergency"])

        mock_drill = detect_emergency("scheduled mock drill for fire safety practice")
        self.assertFalse(mock_drill["is_emergency"])

        # Override scenario: "no fire drill today, real fire" MUST escalate
        override = detect_emergency("no fire drill today, real fire")
        self.assertTrue(override["is_emergency"])
        self.assertEqual(override["trigger"], "FIRE")

        override2 = detect_emergency("this is not a drill, heavy smoke rising from basement")
        self.assertTrue(override2["is_emergency"])
        self.assertEqual(override2["trigger"], "SMOKE")

    def test_non_emergency_routine_complaints(self):
        tap = detect_emergency("washbasin tap is dripping water slowly, plumber needed")
        self.assertFalse(tap["is_emergency"])
        self.assertIsNone(tap["trigger"])

        treadmill = detect_emergency("gym treadmill belt makes loud sound when running")
        self.assertFalse(treadmill["is_emergency"])


class TestClassifier(unittest.TestCase):
    """Verifies local scikit-learn classifier pipeline and fallback behaviors."""

    @patch("backend.app.ml.classifier.settings.GROQ_API_KEY", "")
    def test_local_model_prediction(self):
        res = predict_category_and_urgency("Main pipe burst flooding kitchen floor rapidly", groq_api_key="")
        self.assertEqual(res["category"], "PLUMBING")
        self.assertEqual(res["urgency"], "CRITICAL")
        self.assertEqual(res["provider"], "local_nb")
        self.assertTrue(res["fallback_used"])
        self.assertFalse(res["needs_human_review"])
        self.assertGreater(res["confidence"], 0.5)

    @patch("backend.app.ml.classifier.settings.GROQ_API_KEY", "")
    def test_local_multilingual_lift_prediction(self):
        res = predict_category_and_urgency("lift beech me band ho gayi hai 4th floor par", groq_api_key="")
        self.assertEqual(res["category"], "LIFT")
        self.assertFalse(res["needs_human_review"])

    @patch("backend.app.ml.classifier.settings.GROQ_API_KEY", "")
    def test_unclassified_empty_and_gibberish(self):
        empty_res = predict_category_and_urgency("  ", groq_api_key="")
        self.assertEqual(empty_res["category"], "UNCLASSIFIED")
        self.assertTrue(empty_res["needs_human_review"])

        gibberish_res = predict_category_and_urgency("xyz", groq_api_key="")
        self.assertEqual(gibberish_res["category"], "UNCLASSIFIED")
        self.assertTrue(gibberish_res["needs_human_review"])

    @patch("backend.app.ml.classifier._call_groq_api")
    def test_groq_success_provider(self, mock_groq):
        mock_groq.return_value = {"category": "ELECTRICAL", "urgency": "HIGH"}
        res = predict_category_and_urgency("AC switchboard sparking violently", groq_api_key="gsk_test_mock_key_123")
        self.assertEqual(res["category"], "ELECTRICAL")
        self.assertEqual(res["urgency"], "HIGH")
        self.assertEqual(res["provider"], "groq")
        self.assertFalse(res["fallback_used"])
        self.assertFalse(res["needs_human_review"])

    @patch("backend.app.ml.classifier._call_groq_api")
    def test_groq_failure_triggers_fallback(self, mock_groq):
        # Groq returns None on error or timeout
        mock_groq.return_value = None
        res = predict_category_and_urgency("Water pipe burst in kitchen ceiling", groq_api_key="gsk_test_failing_key")
        self.assertEqual(res["category"], "PLUMBING")
        self.assertEqual(res["provider"], "local_nb")
        self.assertTrue(res["fallback_used"])

    @patch("backend.app.ml.classifier.time.sleep")
    @patch("httpx.Client.post")
    def test_groq_429_rate_limit_backoff_and_retry(self, mock_post, mock_sleep):
        """Groq 429 rate limit triggers backoff sleep and retries once."""
        resp_429 = MagicMock(status_code=429, headers={"retry-after": "1.5"})
        resp_200 = MagicMock(
            status_code=200,
            json=lambda: {"choices": [{"message": {"content": '{"category": "PLUMBING", "urgency": "HIGH"}'}}]},
        )
        mock_post.side_effect = [resp_429, resp_200]
        res = predict_category_and_urgency("Kitchen pipe leaking under sink", groq_api_key="gsk_test_key_429")
        self.assertEqual(res["provider"], "groq")
        self.assertEqual(res["category"], "PLUMBING")
        self.assertEqual(res["urgency"], "HIGH")
        mock_sleep.assert_called_with(1.5)

    @patch("httpx.Client.post")
    def test_groq_timeout_triggers_local_fallback(self, mock_post):
        """Groq timeout triggers clean fallback to local scikit-learn model."""
        import httpx

        mock_post.side_effect = httpx.TimeoutException("Read timeout after 5.0s")
        res = predict_category_and_urgency(
            "Main water pipe burst flooding kitchen", groq_api_key="gsk_test_key_timeout"
        )
        self.assertEqual(res["provider"], "local_nb")
        self.assertTrue(res["fallback_used"])
        self.assertEqual(res["category"], "PLUMBING")

    @patch("httpx.Client.post")
    def test_groq_5xx_server_error_triggers_local_fallback(self, mock_post):
        """Groq 500/503 server error triggers clean fallback to local model."""
        mock_post.return_value = MagicMock(status_code=503, text="Service Unavailable")
        res = predict_category_and_urgency("Main water pipe burst flooding kitchen", groq_api_key="gsk_test_key_503")
        self.assertEqual(res["provider"], "local_nb")
        self.assertTrue(res["fallback_used"])
        self.assertEqual(res["category"], "PLUMBING")

    @patch("httpx.Client.post")
    def test_groq_malformed_json_triggers_local_fallback(self, mock_post):
        """Groq response with broken JSON triggers clean fallback to local model."""
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"choices": [{"message": {"content": "INVALID_JSON_NO_BRACKETS"}}]}
        )
        res = predict_category_and_urgency(
            "Main water pipe burst flooding kitchen", groq_api_key="gsk_test_key_broken_json"
        )
        self.assertEqual(res["provider"], "local_nb")
        self.assertTrue(res["fallback_used"])
        self.assertEqual(res["category"], "PLUMBING")

    @patch("httpx.Client.post")
    def test_groq_invalid_category_triggers_local_fallback(self, mock_post):
        """Groq response with invalid category triggers local fallback."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"choices": [{"message": {"content": '{"category": "ASTRONOMY", "urgency": "HIGH"}'}}]},
        )
        res = predict_category_and_urgency(
            "Main water pipe burst flooding kitchen", groq_api_key="gsk_test_key_invalid_cat"
        )
        self.assertEqual(res["provider"], "local_nb")
        self.assertTrue(res["fallback_used"])
        self.assertEqual(res["category"], "PLUMBING")

    @patch("httpx.Client.post")
    def test_groq_missing_key_triggers_local_fallback(self, mock_post):
        """Groq response missing urgency key triggers local fallback."""
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"choices": [{"message": {"content": '{"category": "PLUMBING"}'}}]}
        )
        res = predict_category_and_urgency(
            "Main water pipe burst flooding kitchen", groq_api_key="gsk_test_key_missing_key"
        )
        self.assertEqual(res["provider"], "local_nb")
        self.assertTrue(res["fallback_used"])
        self.assertEqual(res["category"], "PLUMBING")

    def test_emergency_escalation_when_provider_down_or_returns_low(self):
        """
        Emergency rule engine overrides and escalates even if AI provider is down or returns LOW.
        Deterministic safety invariant: Life safety phrases must NEVER be downgraded.
        """
        emergency_text = "Severe fire breaking out on floor 5 lobby, people trapped!"
        em_res = detect_emergency(emergency_text)
        self.assertTrue(em_res["is_emergency"])
        self.assertEqual(em_res["trigger"], "FIRE")

        mock_ai_output = {"category": "GENERAL", "urgency": "LOW"}
        effective_urgency = "CRITICAL" if em_res["is_emergency"] else mock_ai_output["urgency"]
        self.assertEqual(effective_urgency, "CRITICAL")

    def test_human_correction_beating_late_ai(self):
        """
        Simulate human help desk correction beating late AI classification via version locking.
        Human correction increments version to 2; stale AI update with version 1 is rejected.
        """
        import uuid

        from fastapi import HTTPException

        from backend.app.core.database import SessionLocal
        from backend.app.models.entities import Complaint, Flat, User
        from backend.app.services.complaints import correct_classification

        db = SessionLocal()
        try:
            admin = db.query(User).filter(User.phone == "9876543200").first()
            self.assertIsNotNone(admin)
            flat = db.query(Flat).first()
            self.assertIsNotNone(flat)

            comp = Complaint(
                ticket_number=f"CMP-TEST-{uuid.uuid4().hex[:6].upper()}",
                flat_id=flat.id,
                tower_id=flat.tower_id,
                user_id=admin.id,
                title="Sparking wire",
                description="Wires sparking in switchboard",
                category="GENERAL",
                urgency="LOW",
                status="SUBMITTED",
                version=1,
            )
            db.add(comp)
            db.commit()

            # 1. Human reviewer corrects classification to ELECTRICAL / HIGH
            correct_classification(
                db=db,
                complaint=comp,
                new_category="ELECTRICAL",
                new_urgency="HIGH",
                reason="Verified sparking wires hazard",
                expected_version=1,
                actor_user=admin,
                actor_role="HELPDESK",
            )
            db.commit()
            db.refresh(comp)
            self.assertEqual(comp.version, 2)
            self.assertEqual(comp.category, "ELECTRICAL")

            # 2. Late AI returns and attempts to apply update with expected_version=1
            with self.assertRaises(HTTPException) as ctx:
                correct_classification(
                    db=db,
                    complaint=comp,
                    new_category="COMMON_AREA",
                    new_urgency="LOW",
                    reason="Late AI inference result",
                    expected_version=1,
                    actor_user=admin,
                    actor_role="HELPDESK",
                )
            self.assertEqual(ctx.exception.status_code, 409)
            self.assertIn("optimistic lock conflict", ctx.exception.detail.lower())
            # Complaint remains as corrected by human
            db.refresh(comp)
            self.assertEqual(comp.category, "ELECTRICAL")
            self.assertEqual(comp.version, 2)
        finally:
            db.close()


class TestDuplicateDetector(unittest.TestCase):
    """Verifies character n-gram cosine similarity candidate discovery."""

    def setUp(self):
        self.existing = [
            {"id": "comp-1", "text": "Main water pipe burst in kitchen flooding hallway", "tower_id": "T01"},
            {"id": "comp-2", "text": "Gym treadmill belt slips when running above 6 kmph", "tower_id": "T01"},
            {"id": "comp-3", "text": "Loud music playing in flat 1204 late night", "tower_id": "T02"},
        ]

    def test_detects_near_duplicate(self):
        new_text = "Kitchen main pipe burst water flooding flat living room"
        candidates = find_duplicate_candidates(new_text, self.existing, threshold=0.45)
        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["id"], "comp-1")
        self.assertGreater(candidates[0]["similarity_score"], 0.50)

    def test_excludes_unrelated_complaint(self):
        new_text = "Badminton court net is torn from the post"
        candidates = find_duplicate_candidates(new_text, self.existing, threshold=0.45)
        self.assertEqual(len(candidates), 0)

    def test_tower_filtering(self):
        new_text = "Main water pipe burst in kitchen flooding hallway"
        # Search restricted to Tower 2 should find no candidate since comp-1 is in Tower 1
        candidates = find_duplicate_candidates(new_text, self.existing, threshold=0.45, tower_id="T02")
        self.assertEqual(len(candidates), 0)


if __name__ == "__main__":
    unittest.main()
