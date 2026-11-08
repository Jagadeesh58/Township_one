"""
Unit tests for Township One Machine Learning and Emergency Services.

Verifies:
- Dataset integrity, balance, and schema compliance in complaints_v1.csv
- Deterministic emergency detector across English, Hindi, and Marathi with conservative negation
- Classifier local Naive Bayes pipeline and Groq fallback mechanism
- Character n-gram TF-IDF duplicate candidate finder
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from backend.app.ml.emergency import detect_emergency
from backend.app.ml.classifier import (
    predict_category_and_urgency,
    train_model,
    VALID_CATEGORIES,
    VALID_URGENCIES,
    DEFAULT_DATA_PATH,
)
from backend.app.ml.duplicates import find_duplicate_candidates


class TestComplaintsDataset(unittest.TestCase):
    """Verifies dataset schema, volume, and class balance requirements."""

    def setUp(self):
        self.assertTrue(os.path.exists(DEFAULT_DATA_PATH), f"Missing dataset at {DEFAULT_DATA_PATH}")
        self.df = pd.read_csv(DEFAULT_DATA_PATH)

    def test_minimum_row_count(self):
        """Must contain >= 300 labelled complaints."""
        self.assertGreaterEqual(len(self.df), 300)

    def test_required_columns(self):
        """Must contain all required column definitions."""
        expected_cols = {"text", "category", "urgency", "language", "incident_family"}
        self.assertTrue(expected_cols.issubset(set(self.df.columns)))

    def test_categories_valid_and_balanced(self):
        """All 8 categories must be valid and equally represented."""
        unique_cats = set(self.df["category"].unique())
        self.assertEqual(unique_cats, set(VALID_CATEGORIES))
        cat_counts = self.df["category"].value_counts()
        # Each category should have 45 samples
        for cat in VALID_CATEGORIES:
            self.assertEqual(cat_counts[cat], 45)

    def test_urgencies_valid_and_balanced(self):
        """All 4 urgencies must be valid and well-balanced."""
        unique_urgs = set(self.df["urgency"].unique())
        self.assertEqual(unique_urgs, set(VALID_URGENCIES))
        urg_counts = self.df["urgency"].value_counts()
        for urg in VALID_URGENCIES:
            self.assertGreaterEqual(urg_counts[urg], 80)
            self.assertLessEqual(urg_counts[urg], 100)

    def test_languages_balanced(self):
        """Must cover English, Hindi, and Marathi evenly."""
        lang_counts = self.df["language"].value_counts()
        self.assertEqual(set(lang_counts.keys()), {"en", "hi", "mr"})
        for lang in ["en", "hi", "mr"]:
            self.assertEqual(lang_counts[lang], 120)

    def test_incident_families_count(self):
        """Must contain 40 incident families (5 per category)."""
        self.assertEqual(self.df["incident_family"].nunique(), 40)


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

    def test_local_model_prediction(self):
        res = predict_category_and_urgency("Main pipe burst flooding kitchen floor rapidly")
        self.assertEqual(res["category"], "PLUMBING")
        self.assertEqual(res["urgency"], "CRITICAL")
        self.assertEqual(res["provider"], "local_nb")
        self.assertTrue(res["fallback_used"])
        self.assertFalse(res["needs_human_review"])
        self.assertGreater(res["confidence"], 0.5)

    def test_local_multilingual_lift_prediction(self):
        res = predict_category_and_urgency("lift beech me band ho gayi hai 4th floor par")
        self.assertEqual(res["category"], "LIFT")
        self.assertFalse(res["needs_human_review"])

    def test_unclassified_empty_and_gibberish(self):
        empty_res = predict_category_and_urgency("  ")
        self.assertEqual(empty_res["category"], "UNCLASSIFIED")
        self.assertTrue(empty_res["needs_human_review"])

        gibberish_res = predict_category_and_urgency("xyz")
        self.assertEqual(gibberish_res["category"], "UNCLASSIFIED")
        self.assertTrue(gibberish_res["needs_human_review"])

    @patch("backend.app.ml.classifier._call_groq_api")
    def test_groq_success_provider(self, mock_groq):
        mock_groq.return_value = {"category": "ELECTRICAL", "urgency": "HIGH"}
        res = predict_category_and_urgency(
            "AC switchboard sparking violently",
            groq_api_key="gsk_test_mock_key_123"
        )
        self.assertEqual(res["category"], "ELECTRICAL")
        self.assertEqual(res["urgency"], "HIGH")
        self.assertEqual(res["provider"], "groq")
        self.assertFalse(res["fallback_used"])
        self.assertFalse(res["needs_human_review"])

    @patch("backend.app.ml.classifier._call_groq_api")
    def test_groq_failure_triggers_fallback(self, mock_groq):
        # Groq returns None on error or timeout
        mock_groq.return_value = None
        res = predict_category_and_urgency(
            "Water pipe burst in kitchen ceiling",
            groq_api_key="gsk_test_failing_key"
        )
        self.assertEqual(res["category"], "PLUMBING")
        self.assertEqual(res["provider"], "local_nb")
        self.assertTrue(res["fallback_used"])


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
