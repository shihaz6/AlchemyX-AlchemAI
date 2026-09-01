"""Evaluate AlchemyX retrieval and answer quality."""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from alchemyx.main import create_system


def load_questions(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def expected_chunk_rank(documents, expected_chunk):
    for rank, document in enumerate(documents, start=1):
        if document.id == expected_chunk:
            return rank

    return None


def evaluate_questions(system, questions):
    rows = []

    for item in questions:
        start_time = time.perf_counter()
        result = system.ask(item["question"])
        latency = time.perf_counter() - start_time
        rank = expected_chunk_rank(
            result.get("documents", []),
            item.get("expected_chunk"),
        )
        answer = result.get("answer", "")

        rows.append(
            {
                "question": item["question"],
                "expected_source": item.get("expected_source"),
                "expected_chunk": item.get("expected_chunk"),
                "retrieval_hit": rank is not None and rank <= 5,
                "expected_chunk_rank": rank,
                "iterations": result.get("iterations", 0),
                "sufficiency_reached": result.get("stop_reason")
                == "sufficient_evidence",
                "answer_produced": bool(answer.strip()),
                "latency": latency,
            }
        )

    return rows


def summarize(rows):
    if not rows:
        return {
            "recall_at_5": 0.0,
            "mrr": 0.0,
            "average_iterations": 0.0,
            "success_rate": 0.0,
            "average_latency": 0.0,
        }

    reciprocal_ranks = [
        1.0 / row["expected_chunk_rank"]
        for row in rows
        if row["expected_chunk_rank"]
    ]

    return {
        "recall_at_5": sum(row["retrieval_hit"] for row in rows) / len(rows),
        "mrr": sum(reciprocal_ranks) / len(rows),
        "average_iterations": sum(row["iterations"] for row in rows) / len(rows),
        "success_rate": sum(row["sufficiency_reached"] for row in rows) / len(rows),
        "average_latency": sum(row["latency"] for row in rows) / len(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--questions",
        default="data/sample_questions.json",
        help="Path to evaluation questions JSON.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional path to write detailed JSON results.",
    )
    args = parser.parse_args()

    questions = load_questions(args.questions)
    system = create_system()
    rows = evaluate_questions(system, questions)
    metrics = summarize(rows)

    print(json.dumps(metrics, indent=2))

    if args.output:
        output = {
            "metrics": metrics,
            "rows": rows,
        }
        Path(args.output).write_text(
            json.dumps(output, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
