from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult


class FakeRetrievalPipeline:

    def query(self, query):

        if query == "Which equipment is affected when Component Y fails?":
            return [
                RetrievalResult(
                    id="doc_1",
                    text="Component Y controls the coolant flow.",
                    source_doc="fake",
                    chunk_index=0,
                    score=1.0,
                ),
                RetrievalResult(
                    id="doc_2",
                    text="Component Y failure causes loss of coolant flow.",
                    source_doc="fake",
                    chunk_index=1,
                    score=0.9,
                ),
            ]

        if query == "equipment affected by Component Y failure":
            return [
                RetrievalResult(
                    id="doc_3",
                    text="Loss of coolant flow affects Reactor Pump A.",
                    source_doc="fake",
                    chunk_index=2,
                    score=1.0,
                )
            ]

        return []
