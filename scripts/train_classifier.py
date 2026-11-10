"""
Township One - Reproducible Complaint Classifier Training Script.

Trains the Naive Bayes category and urgency classification pipelines
using complaints_v1.csv with a deterministic fixed seed (seed=42).
"""

import os
import sys

# Ensure project root is on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.ml.classifier import DEFAULT_DATA_PATH, DEFAULT_MODEL_PATH, train_model  # noqa: E402


def main():
    print("=" * 60)
    print("Township One - Training Classifier Model")
    print(f"Data source : {DEFAULT_DATA_PATH}")
    print(f"Output model: {DEFAULT_MODEL_PATH}")
    print("Fixed seed  : 42")
    print("=" * 60)

    cat_pipeline, urg_pipeline = train_model(csv_path=DEFAULT_DATA_PATH, save_path=DEFAULT_MODEL_PATH, random_seed=42)

    print("\nTraining completed successfully!")
    print(f"Category classes ({len(cat_pipeline.classes_)}): {list(cat_pipeline.classes_)}")
    print(f"Urgency classes ({len(urg_pipeline.classes_)}): {list(urg_pipeline.classes_)}")
    print("Model artifact successfully serialized and verified.")


if __name__ == "__main__":
    main()
