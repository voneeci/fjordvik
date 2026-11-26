"""Phase 3: failure risk. Each pump gets a daily score, the chance it fails in the next 30
days from readings up to that day, and an alert level set from the cost of a missed failure
against a wasted visit.

Measured on synthetic data with planted signals: Fjordvik Manufacturing Oy is fictional.
"""

MODEL_VERSION = "ml-1.0.0"
DATA_BASIS = "synthetic data with planted signals"
LIBRARIES = ["numpy", "pandas", "scipy", "scikit-learn", "joblib", "threadpoolctl"]
