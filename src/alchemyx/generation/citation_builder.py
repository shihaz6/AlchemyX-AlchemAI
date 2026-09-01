def build_citations(documents):
    citations = []
    seen_ids = set()

    for document in documents:
        if document.id in seen_ids:
            continue

        seen_ids.add(document.id)
        citations.append(
            {
                "id": document.id,
                "source": document.source_doc,
                "chunk_index": document.chunk_index,
            }
        )

    return citations


def format_citations(documents):
    lines = []
    for index, citation in enumerate(build_citations(documents), start=1):
        lines.append(
            f"[{index}] {citation['source']} - chunk {citation['chunk_index']}"
        )

    return "\n".join(lines)
