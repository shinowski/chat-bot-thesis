"""
test_semantic.py
-----------------
Step 2 of the plan: turn manual spot-checks into a real evaluation —
accuracy, per-intent precision/recall/F1, and a confusion matrix,
run over the full held-out set in test_cases.py instead of 10
hand-picked messages.

Wired directly to your real model/intent_classifier.py. This loads
the already-trained semantic_classifier.pkl (same file your own
test_semantic.py loads) rather than retraining, so run
train_semantic.py first if you haven't already / if intents.json
changed since your last training run.

Run from your project root (the directory containing model/ and
data/), same as your existing train_semantic.py / test_semantic.py:

    python eval/test_semantic.py
"""

from __future__ import annotations
import sys
import os
from collections import defaultdict

# so `model.intent_classifier` resolves the same way it does for your
# existing train_semantic.py / test_semantic.py at the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from model.intent_classifier import IntentClassifier  # noqa: E402
from test_cases import TEST_CASES  # noqa: E402

CONFIDENCE_WARN_THRESHOLD = 0.55  # flag correct-but-shaky predictions

_classifier = IntentClassifier()
_classifier.load("semantic_classifier.pkl")


def predict(text: str):
    """Thin wrapper around your real classifier so the rest of this
    file doesn't need to know anything about sklearn/MiniLM."""
    intent, confidence = _classifier.predict(text)
    return intent, confidence


# =======================================================================
# Everything below this line should NOT need to change.
# =======================================================================

def run_predictions():
    rows = []
    for text, expected, note in TEST_CASES:
        predicted, confidence = predict(text)
        rows.append({
            "text": text,
            "expected": expected,
            "predicted": predicted,
            "confidence": confidence,
            "correct": predicted == expected,
            "note": note,
        })
    return rows


def compute_metrics(rows, labels):
    """
    Manual precision/recall/F1/confusion-matrix computation —
    no sklearn dependency required. Swap in
    sklearn.metrics.classification_report if you prefer; results
    should match.
    """
    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)
    confusion = {a: {b: 0 for b in labels} for a in labels}

    for r in rows:
        confusion[r["expected"]][r["predicted"]] += 1
        if r["predicted"] == r["expected"]:
            tp[r["expected"]] += 1
        else:
            fn[r["expected"]] += 1
            fp[r["predicted"]] += 1

    per_intent = {}
    for label in labels:
        precision = tp[label] / (tp[label] + fp[label]) if (tp[label] + fp[label]) else 0.0
        recall = tp[label] / (tp[label] + fn[label]) if (tp[label] + fn[label]) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        support = tp[label] + fn[label]
        per_intent[label] = {
            "precision": precision, "recall": recall, "f1": f1, "support": support
        }

    accuracy = sum(1 for r in rows if r["correct"]) / len(rows)
    return accuracy, per_intent, confusion


def print_report(rows, labels):
    accuracy, per_intent, confusion = compute_metrics(rows, labels)

    print("=" * 50)
    print("FLAMMA SEMANTIC EVALUATION")
    print("=" * 50)
    print(f"\nAccuracy: {accuracy * 100:.2f}%  ({sum(r['correct'] for r in rows)}/{len(rows)})\n")

    print(f"{'':14s} {'precision':>10s} {'recall':>10s} {'f1-score':>10s} {'support':>9s}")
    for label in labels:
        m = per_intent[label]
        print(f"{label:14s} {m['precision']:10.2f} {m['recall']:10.2f} {m['f1']:10.2f} {m['support']:9d}")

    macro_p = sum(m["precision"] for m in per_intent.values()) / len(labels)
    macro_r = sum(m["recall"] for m in per_intent.values()) / len(labels)
    macro_f1 = sum(m["f1"] for m in per_intent.values()) / len(labels)
    print(f"\n{'macro avg':14s} {macro_p:10.2f} {macro_r:10.2f} {macro_f1:10.2f} {len(rows):9d}")

    # ---- confusion matrix ----
    print("\n" + "=" * 50)
    print("CONFUSION MATRIX (rows = expected, cols = predicted)")
    print("=" * 50)
    short = {l: l[:6] for l in labels}
    header = "expected\\pred".ljust(14) + "".join(f"{short[l]:>8s}" for l in labels)
    print(header)
    for a in labels:
        row_str = a.ljust(14) + "".join(f"{confusion[a][b]:>8d}" for b in labels)
        print(row_str)

    # ---- misclassifications, worst first ----
    print("\n" + "=" * 50)
    print("MISCLASSIFICATIONS")
    print("=" * 50)
    errors = [r for r in rows if not r["correct"]]
    if not errors:
        print("None — every test case was classified correctly.")
    else:
        for r in errors:
            note = f"  [{r['note']}]" if r["note"] else ""
            print(f"  '{r['text']}'")
            print(f"    expected={r['expected']}  predicted={r['predicted']}  confidence={r['confidence']:.3f}{note}")

    # ---- correct but low-confidence, worth watching ----
    shaky = [r for r in rows if r["correct"] and r["confidence"] < CONFIDENCE_WARN_THRESHOLD]
    if shaky:
        print("\n" + "=" * 50)
        print(f"LOW-CONFIDENCE (correct but < {CONFIDENCE_WARN_THRESHOLD})")
        print("=" * 50)
        for r in shaky:
            print(f"  '{r['text']}'  ->  {r['predicted']}  (confidence={r['confidence']:.3f})")

    # ---- pairwise confusion summary, sorted by frequency ----
    print("\n" + "=" * 50)
    print("TOP CONFUSED INTENT PAIRS")
    print("=" * 50)
    pairs = []
    for a in labels:
        for b in labels:
            if a != b and confusion[a][b] > 0:
                pairs.append((confusion[a][b], a, b))
    pairs.sort(reverse=True)
    if not pairs:
        print("None.")
    else:
        for count, a, b in pairs[:10]:
            print(f"  {a} -> predicted as {b}   ({count}x)")


if __name__ == "__main__":
    labels = sorted({t[1] for t in TEST_CASES})
    rows = run_predictions()
    print_report(rows, labels)
