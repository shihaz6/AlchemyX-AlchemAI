class FakeRetrievalPipeline:

    def __init__(self):

        self.data = {

            "Component Y": [
                {
                    "id": "doc_1",
                    "text": (
                        "Component Y controls the coolant flow."
                    )
                },
                {
                    "id": "doc_2",
                    "text": (
                        "Component Y failure causes loss "
                        "of coolant flow."
                    )
                }
            ],

            "equipment affected by Component Y failure": [
                {
                    "id": "doc_3",
                    "text": (
                        "Loss of coolant flow affects "
                        "Reactor Pump A."
                    )
                }
            ]
        }

    def query(self, query):

        if query == "Which equipment is affected when Component Y fails?":
            return [
                {
                    "id": "doc_1",
                    "text": (
                        "Component Y controls the coolant flow."
                    )
                },
                {
                    "id": "doc_2",
                    "text": (
                        "Component Y failure causes loss "
                        "of coolant flow."
                    )
                }
            ]

        if query == "equipment affected by Component Y failure":
            return [
                {
                    "id": "doc_3",
                    "text": (
                        "Loss of coolant flow affects "
                        "Reactor Pump A."
                    )
                }
            ]

        return []