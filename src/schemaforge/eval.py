"""Field-level precision and recall evaluation for a JSONL gold file."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from schemaforge.models import InputRecord


@dataclass(frozen=True)
class EvaluationMetrics:
    records: int
    precision: float
    recall: float


def evaluate_predictions(
    inputs: list[InputRecord], predictions: list[dict[str, Any]], gold: list[dict[str, Any]]
) -> EvaluationMetrics:
    """Compare normalized field values across records."""
    if not (len(inputs) == len(predictions) == len(gold)):
        raise ValueError("inputs, predictions and gold must have equal lengths")
    predicted_fields = 0
    correct_fields = 0
    gold_fields = 0
    for prediction, expected in zip(predictions, gold, strict=True):
        for key, value in prediction.items():
            if value is not None:
                predicted_fields += 1
                if value == expected.get(key):
                    correct_fields += 1
        gold_fields += sum(value is not None for value in expected.values())
    return EvaluationMetrics(
        records=len(inputs),
        precision=correct_fields / predicted_fields if predicted_fields else 0.0,
        recall=correct_fields / gold_fields if gold_fields else 0.0,
    )
