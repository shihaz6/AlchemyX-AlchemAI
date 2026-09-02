from time import perf_counter
from uuid import uuid4

from ..config import MAX_AGENT_ITERATIONS
from ..telemetry import log, reset_run_id, set_run_id


class AgentLoop:
    MAX_ITERATIONS = MAX_AGENT_ITERATIONS

    def __init__(self, retrieval_pipeline, sufficiency_checker):
        self.retrieval_pipeline = retrieval_pipeline
        self.sufficiency_checker = sufficiency_checker

    def run(self, question, run_id=None):
        original_question = question
        research_run_id = run_id or uuid4().hex[:6]
        token = set_run_id(research_run_id)
        started = perf_counter()
        all_documents = []
        seen_document_ids = set()
        current_query = original_question
        previous_queries = set()
        result = None
        try:
            for iteration in range(self.MAX_ITERATIONS):
                iteration_started = perf_counter()
                log(f"ITERATION {iteration + 1}")
                log(f"Query: {current_query}")
                retrieved = self.retrieval_pipeline.query(current_query)
                for document in retrieved:
                    if document.id not in seen_document_ids:
                        all_documents.append(document)
                        seen_document_ids.add(document.id)

                if not retrieved and not all_documents:
                    return self._result([], None, iteration + 1, "no_retrieval_results", research_run_id)

                # Follow-up queries affect retrieval only. The checker always
                # evaluates the exact original user question.
                result = self.sufficiency_checker.check(original_question, all_documents)
                log(f"Sufficient: {result.sufficient}")
                log(f"Missing: {result.missing}")
                log(f"Iteration {iteration + 1} total: {perf_counter() - iteration_started:.2f}s")

                if result.sufficient:
                    return self._result(all_documents, result, iteration + 1, "sufficient_evidence", research_run_id)
                if not result.search_queries:
                    return self._result(all_documents, result, iteration + 1, "no_search_query", research_run_id)

                next_query = result.search_queries[0]
                previous_queries.add(current_query)
                if next_query in previous_queries:
                    return self._result(all_documents, result, iteration + 1, "repeated_query", research_run_id)
                current_query = next_query

            return self._result(all_documents, result, self.MAX_ITERATIONS, "max_iterations", research_run_id)
        finally:
            log(f"TOTAL: {perf_counter() - started:.2f}s")
            reset_run_id(token)

    @staticmethod
    def _result(documents, result, iterations, stop_reason, research_run_id):
        return {
            "documents": documents,
            "result": result,
            "iterations": iterations,
            "stop_reason": stop_reason,
            "research_run_id": research_run_id,
        }
