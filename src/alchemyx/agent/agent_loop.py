class AgentLoop:

    MAX_ITERATIONS = 4

    def __init__(self, retrieval_pipeline, sufficiency_checker):

        self.retrieval_pipeline = retrieval_pipeline
        self.sufficiency_checker = sufficiency_checker

    def run(self, question):

        all_documents = []
        seen_document_ids = set()

        current_query = question
        previous_queries = set()

        for iteration in range(self.MAX_ITERATIONS):

            print(f"\n===== ITERATION {iteration + 1} =====")
            print(f"Query: {current_query}")

            # 1. Retrieve documents
            retrieved = self.retrieval_pipeline.query(
                current_query
            )

            # 2. Add only new documents
            for document in retrieved:

                document_id = document.id

                if document_id not in seen_document_ids:

                    all_documents.append(document)
                    seen_document_ids.add(document_id)

            # 3. Check sufficiency
            result = self.sufficiency_checker.check(
                question,
                all_documents
            )

            print("Sufficient:", result.sufficient)
            print("Missing:", result.missing)

            # 4. Stop if enough evidence exists
            if result.sufficient:

                print("\nStopping: sufficient evidence found.")

                return {
                    "documents": all_documents,
                    "result": result,
                    "iterations": iteration + 1,
                    "stop_reason": "sufficient_evidence"
                }

            # 5. Stop if no search query was generated
            if not result.search_queries:

                print(
                    "\nStopping: no actionable search query."
                )

                return {
                    "documents": all_documents,
                    "result": result,
                    "iterations": iteration + 1,
                    "stop_reason": "no_search_query"
                }

            # 6. Select next query
            next_query = result.search_queries[0]
            previous_queries.add(current_query)

            # 7. Prevent repeated queries
            if next_query in previous_queries:

                print(
                    "\nStopping: repeated search query."
                )

                return {
                    "documents": all_documents,
                    "result": result,
                    "iterations": iteration + 1,
                    "stop_reason": "repeated_query"
                }

            current_query = next_query

        # Maximum iterations reached
        print(
            "\nStopping: maximum iterations reached."
        )

        return {
            "documents": all_documents,
            "result": result,
            "iterations": self.MAX_ITERATIONS,
            "stop_reason": "max_iterations"
        }
