from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4

from .agent.agent_loop import AgentLoop
from .agent.openrouter_client import OpenRouterClient
from .agent.sufficiency_checker import SufficiencyChecker
from .generation.answer_generator import AnswerGenerator
from .generation.citation_builder import build_citations
from .retrieval.main import create_agent_retrieval_pipeline
from .telemetry import log, reset_run_id, set_run_id


@dataclass
class AlchemyXSystem:
    agent: AgentLoop
    answer_generator: AnswerGenerator

    def ask(self, question):
        research_run_id = uuid4().hex[:6]
        token = set_run_id(research_run_id)
        try:
            # AgentLoop generates its own ID when called through older/custom
            # implementations; use the returned ID when it provides one.
            agent_result = self.agent.run(question)
            research_run_id = agent_result.get("research_run_id", research_run_id)
            reset_run_id(token)
            token = set_run_id(research_run_id)
            started = perf_counter()
            generated_answer = self.answer_generator.generate(
                question=question,
                documents=agent_result["documents"],
                sufficiency_result=agent_result["result"],
            )
            log(f"Final generation: {perf_counter() - started:.2f}s")
            citations = build_citations(agent_result["documents"])
        finally:
            reset_run_id(token)

        return {
            "answer": generated_answer.answer,
            "answer_evidence_ids": generated_answer.evidence_ids,
            "citations": citations,
            "documents": agent_result["documents"],
            "sufficiency_result": agent_result["result"],
            "iterations": agent_result["iterations"],
            "stop_reason": agent_result["stop_reason"],
            "research_run_id": research_run_id,
        }


def create_system():
    llm_client = OpenRouterClient()
    retrieval_pipeline = create_agent_retrieval_pipeline()
    sufficiency_checker = SufficiencyChecker(llm_client)
    agent = AgentLoop(retrieval_pipeline, sufficiency_checker)
    answer_generator = AnswerGenerator(llm_client)

    return AlchemyXSystem(
        agent=agent,
        answer_generator=answer_generator,
    )


def ask(question):
    return create_system().ask(question)
