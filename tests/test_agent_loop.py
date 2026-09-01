from src.alchemyx.agent.agent_loop import AgentLoop
from src.alchemyx.agent.openrouter_client import OpenRouterClient
from src.alchemyx.agent.sufficiency_checker import SufficiencyChecker
from tests.fake_retrieval import FakeRetrievalPipeline


def main():

    retrieval_pipeline = FakeRetrievalPipeline()

    llm_client = OpenRouterClient()

    checker = SufficiencyChecker(
        llm_client
    )

    agent = AgentLoop(
        retrieval_pipeline,
        checker
    )

    question = (
        "Which equipment is affected when Component Y fails?"
    )

    result = agent.run(question)

    print("\n========== FINAL ==========\n")

    print("Iterations:")
    print(result["iterations"])

    print("\nStop reason:")
    print(result["stop_reason"])

    print("\nFinal sufficiency:")
    print(result["result"].sufficient)

    print("\nMissing:")
    print(result["result"].missing)

    print("\nDocuments used:")

    for document in result["documents"]:

        print(
            document["id"],
            ":",
            document["text"]
        )


if __name__ == "__main__":
    main()