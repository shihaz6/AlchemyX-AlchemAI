from alchemyx.agent.openrouter_client import OpenRouterClient
from src.alchemyx.agent.sufficiency_checker import SufficiencyChecker


def main():

    documents = [
        {
            "id": "doc_1",
            "text": (
                "Component Y controls the coolant flow "
                "in Reactor Unit 4."
            )
        },
        {
            "id": "doc_2",
            "text": (
                "When Component Y fails, coolant flow "
                "stops."
            )
        },
        {
            "id": "doc_3",
            "text": (
                "Loss of coolant flow affects Reactor Pump A."
            )
        }
    ]

    question = (
        "Which equipment is affected when Component Y fails?"
    )

    llm_client = OpenRouterClient()

    checker = SufficiencyChecker(
        llm_client
    )

    result = checker.check(
        question,
        documents
    )

    print("\n========== RESULT ==========\n")

    print("Sufficient:")
    print(result.sufficient)

    print("\nMissing:")
    print(result.missing)

    print("\nSearch queries:")
    print(result.search_queries)

    print("\nEvidence IDs:")
    print(result.evidence_ids)

    print("\nReason:")
    print(result.reason)


if __name__ == "__main__":
    main()