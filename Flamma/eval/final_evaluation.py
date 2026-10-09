import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from collections import Counter, defaultdict

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

from model.intent_classifier import IntentClassifier
from eval.final_test_cases import FINAL_TEST_CASES


MODEL_PATH = "semantic_classifier_balanced_v2.pkl"


print("=" * 60)
print("FLAMMA FINAL HELD-OUT SEMANTIC EVALUATION")
print("=" * 60)

# Load model
classifier = IntentClassifier()
classifier.load(MODEL_PATH)

y_true = []
y_pred = []
results = []

print(f"\nModel: {MODEL_PATH}")
print(f"Test cases: {len(FINAL_TEST_CASES)}")
print("\nRunning evaluation...")

for message, expected in FINAL_TEST_CASES:
    predicted, confidence = classifier.predict(message)

    y_true.append(expected)
    y_pred.append(predicted)

    results.append(
        {
            "message": message,
            "expected": expected,
            "predicted": predicted,
            "confidence": confidence,
        }
    )


# =========================================================
# OVERALL ACCURACY
# =========================================================

correct = sum(
    1 for result in results
    if result["expected"] == result["predicted"]
)

total = len(results)
accuracy = accuracy_score(y_true, y_pred)

print("\n" + "=" * 60)
print("OVERALL RESULTS")
print("=" * 60)

print(f"\nCorrect:  {correct}/{total}")
print(f"Errors:   {total - correct}/{total}")
print(f"Accuracy: {accuracy * 100:.2f}%")


# =========================================================
# CLASSIFICATION REPORT
# =========================================================

labels = sorted(set(y_true))

print("\n" + "=" * 60)
print("CLASSIFICATION REPORT")
print("=" * 60)

print(
    classification_report(
        y_true,
        y_pred,
        labels=labels,
        digits=2,
        zero_division=0,
    )
)


# =========================================================
# CONFUSION MATRIX
# =========================================================

cm = confusion_matrix(
    y_true,
    y_pred,
    labels=labels,
)

print("=" * 60)
print("CONFUSION MATRIX")
print("Rows = expected | Columns = predicted")
print("=" * 60)

header = "expected\\pred".ljust(16)

for label in labels:
    header += label[:7].rjust(8)

print(header)

for label, row in zip(labels, cm):
    line = label[:15].ljust(16)

    for value in row:
        line += str(value).rjust(8)

    print(line)


# =========================================================
# MISCLASSIFICATIONS
# =========================================================

errors = [
    result
    for result in results
    if result["expected"] != result["predicted"]
]

print("\n" + "=" * 60)
print(f"MISCLASSIFICATIONS ({len(errors)})")
print("=" * 60)

if not errors:
    print("\nNone.")
else:
    for result in errors:
        print(f"\nMessage:    {result['message']!r}")
        print(f"Expected:   {result['expected']}")
        print(f"Predicted:  {result['predicted']}")
        print(f"Confidence: {result['confidence']:.3f}")


# =========================================================
# PER-INTENT CORRECT COUNTS
# =========================================================

correct_by_intent = Counter()
total_by_intent = Counter(y_true)

for result in results:
    if result["expected"] == result["predicted"]:
        correct_by_intent[result["expected"]] += 1

print("\n" + "=" * 60)
print("PER-INTENT ACCURACY")
print("=" * 60)

for label in labels:
    class_correct = correct_by_intent[label]
    class_total = total_by_intent[label]

    percentage = (
        class_correct / class_total * 100
        if class_total
        else 0
    )

    print(
        f"{label:15} "
        f"{class_correct:2}/{class_total:2} "
        f"({percentage:6.2f}%)"
    )


# =========================================================
# LOW-CONFIDENCE CORRECT PREDICTIONS
# =========================================================

low_confidence = [
    result
    for result in results
    if result["expected"] == result["predicted"]
    and result["confidence"] < 0.55
]

print("\n" + "=" * 60)
print(
    f"LOW-CONFIDENCE CORRECT PREDICTIONS "
    f"(< 0.55): {len(low_confidence)}"
)
print("=" * 60)

for result in low_confidence:
    print(
        f"{result['message']!r} "
        f"-> {result['predicted']} "
        f"({result['confidence']:.3f})"
    )


# =========================================================
# TOP CONFUSED PAIRS
# =========================================================

confused_pairs = defaultdict(int)

for result in errors:
    pair = (
        result["expected"],
        result["predicted"],
    )
    confused_pairs[pair] += 1

print("\n" + "=" * 60)
print("CONFUSED INTENT PAIRS")
print("=" * 60)

if not confused_pairs:
    print("\nNone.")
else:
    for (expected, predicted), count in sorted(
        confused_pairs.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        print(
            f"{expected:15} -> "
            f"{predicted:15} "
            f"{count}x"
        )


print("\n" + "=" * 60)
print("EVALUATION COMPLETE")
print("=" * 60)