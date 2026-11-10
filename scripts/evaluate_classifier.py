"""
Township One - Classifier Evaluation Harness.

Evaluates category and urgency prediction performance using incident-family
grouped held-out test partitioning. Demonstrates cross-family semantic
generalization without leaking incident variants between train and test sets.
Uses standard csv module and scikit-learn without requiring pandas.
"""

import csv
import os
import sys

import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

# Ensure Township One project root is in python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.ml.classifier import (  # noqa: E402
    DEFAULT_DATA_PATH,
    VALID_CATEGORIES,
    VALID_URGENCIES,
    build_pipeline,
)

DATASET_VERSION = "complaints_v1.csv (v1.0)"


def format_support_tag(support: int) -> str:
    """Labels metrics exploratory when sample support is below 20."""
    if support < 20:
        return "[EXPLORATORY - support < 20]"
    return "[VALIDATED - support >= 20]"


def print_table_header(title: str):
    print("\n" + "=" * 80)
    print(f" {title.upper()}")
    print("=" * 80)


def evaluate():
    print_table_header(f"Township One ML Classifier Evaluation - {DATASET_VERSION}")
    print(f"Dataset path: {DEFAULT_DATA_PATH}")

    if not os.path.exists(DEFAULT_DATA_PATH):
        print(f"ERROR: Dataset file not found at {DEFAULT_DATA_PATH}")
        sys.exit(1)

    with open(DEFAULT_DATA_PATH, encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    total_records = len(records)
    unique_families = len(set(r["incident_family"] for r in records))
    print(f"Total labeled records: {total_records}")
    print(f"Unique incident families: {unique_families}")
    print("Grouping strategy: GroupShuffleSplit on 'incident_family'")

    # Balanced category-stratified incident family grouping (zero leakage across train/test)
    # Selects 1 test family per category to ensure every category is evaluated on unseen families
    rng = np.random.RandomState(42)
    test_families = set()
    for cat in VALID_CATEGORIES:
        cat_families = sorted(list(set(r["incident_family"] for r in records if r["category"] == cat)))
        chosen = rng.choice(cat_families, size=1, replace=False)[0]
        test_families.add(chosen)

    train_records = [r for r in records if r["incident_family"] not in test_families]
    test_records = [r for r in records if r["incident_family"] in test_families]

    train_families = set(r["incident_family"] for r in train_records)
    overlap = train_families.intersection(test_families)

    print(f"\nTrain set: {len(train_records)} samples across {len(train_families)} incident families")
    print(f"Held-out test set: {len(test_records)} samples across {len(test_families)} incident families")
    print(f"Family leakage verification: {len(overlap)} overlapping families (strict zero-leakage)")

    # Train category and urgency models on train partition only
    X_train = [r["text"] for r in train_records]
    y_cat_train = [r["category"] for r in train_records]
    y_urg_train = [r["urgency"] for r in train_records]

    X_test = [r["text"] for r in test_records]
    y_cat_test = [r["category"] for r in test_records]
    y_urg_test = [r["urgency"] for r in test_records]

    cat_pipeline = build_pipeline()
    cat_pipeline.fit(X_train, y_cat_train)

    urg_pipeline = build_pipeline()
    urg_pipeline.fit(X_train, y_urg_train)

    cat_preds = cat_pipeline.predict(X_test)
    urg_preds = urg_pipeline.predict(X_test)

    # -------------------------------------------------------------------------
    # Category Performance Table
    # -------------------------------------------------------------------------
    print_table_header("Category Classification Performance (Held-out Unseen Families)")
    cat_prec, cat_rec, cat_f1, cat_supp = precision_recall_fscore_support(
        y_cat_test, cat_preds, labels=VALID_CATEGORIES, zero_division=0
    )

    col_fmt = "{:<16} {:>10} {:>10} {:>10} {:>10}  {:<30}"
    print(col_fmt.format("Category", "Precision", "Recall", "F1-Score", "Support", "Support Reliability Status"))
    print("-" * 90)

    for i, cat_name in enumerate(VALID_CATEGORIES):
        supp = int(cat_supp[i])
        tag = format_support_tag(supp)
        print(col_fmt.format(cat_name, f"{cat_prec[i]:.4f}", f"{cat_rec[i]:.4f}", f"{cat_f1[i]:.4f}", supp, tag))

    cat_acc = accuracy_score(y_cat_test, cat_preds)
    cat_macro_f1 = np.mean(cat_f1)
    print("-" * 90)
    print(f"Category Overall Accuracy : {cat_acc:.4f} ({cat_acc * 100:.1f}%)")
    print(f"Category Macro F1-Score   : {cat_macro_f1:.4f}")

    # -------------------------------------------------------------------------
    # Urgency Performance Table
    # -------------------------------------------------------------------------
    print_table_header("Urgency Classification Performance (Held-out Unseen Families)")
    urg_prec, urg_rec, urg_f1, urg_supp = precision_recall_fscore_support(
        y_urg_test, urg_preds, labels=VALID_URGENCIES, zero_division=0
    )

    print(col_fmt.format("Urgency", "Precision", "Recall", "F1-Score", "Support", "Support Reliability Status"))
    print("-" * 90)

    for i, urg_name in enumerate(VALID_URGENCIES):
        supp = int(urg_supp[i])
        tag = format_support_tag(supp)
        print(col_fmt.format(urg_name, f"{urg_prec[i]:.4f}", f"{urg_rec[i]:.4f}", f"{urg_f1[i]:.4f}", supp, tag))

    urg_acc = accuracy_score(y_urg_test, urg_preds)
    urg_macro_f1 = np.mean(urg_f1)
    print("-" * 90)
    print(f"Urgency Overall Accuracy  : {urg_acc:.4f} ({urg_acc * 100:.1f}%)")
    print(f"Urgency Macro F1-Score    : {urg_macro_f1:.4f}")

    # -------------------------------------------------------------------------
    # Per-Language Breakdown Table
    # -------------------------------------------------------------------------
    print_table_header("Per-Language Performance Breakdown (Held-out Test Partition)")
    lang_col_fmt = "{:<12} {:>10} {:>16} {:>16}  {:<30}"
    print(
        lang_col_fmt.format(
            "Language", "Support", "Category Accuracy", "Urgency Accuracy", "Support Reliability Status"
        )
    )
    print("-" * 90)

    languages = ["en", "hi", "mr"]
    for r, cp, up in zip(test_records, cat_preds, urg_preds, strict=True):
        r["cat_pred"] = cp
        r["urg_pred"] = up

    for lang in languages:
        sub = [r for r in test_records if r.get("language") == lang]
        supp = len(sub)
        if supp > 0:
            y_c = [r["category"] for r in sub]
            y_cp = [r["cat_pred"] for r in sub]
            y_u = [r["urgency"] for r in sub]
            y_up = [r["urg_pred"] for r in sub]
            lang_cat_acc = accuracy_score(y_c, y_cp)
            lang_urg_acc = accuracy_score(y_u, y_up)
            tag = format_support_tag(supp)
            print(
                lang_col_fmt.format(
                    lang,
                    supp,
                    f"{lang_cat_acc:.4f} ({lang_cat_acc * 100:.1f}%)",
                    f"{lang_urg_acc:.4f} ({lang_urg_acc * 100:.1f}%)",
                    tag,
                )
            )
        else:
            print(lang_col_fmt.format(lang, 0, "N/A", "N/A", "[NO DATA]"))

    print("-" * 90)
    print(f"\nEvaluation summary completed cleanly against dataset {DATASET_VERSION}.\n")


if __name__ == "__main__":
    evaluate()
