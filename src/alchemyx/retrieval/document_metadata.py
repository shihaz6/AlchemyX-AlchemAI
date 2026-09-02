from pathlib import Path


def metadata_search_text(metadata):
    if not metadata:
        return ""

    fields = [
        ("FILE", metadata.get("file_name")),
        ("TYPE", metadata.get("document_type")),
        ("EXTENSION", metadata.get("extension")),
        ("PATH", metadata.get("relative_path")),
        ("SOURCE", metadata.get("source_doc")),
        ("KEYWORDS", metadata.get("metadata_keywords")),
    ]
    return "\n".join(
        f"{label}: {value}"
        for label, value in fields
        if value
    )


def build_searchable_text(text, metadata=None):
    header = metadata_search_text(metadata)
    if not header:
        return text
    if not text:
        return header
    return f"{header}\n\n{text}"


def file_metadata(corpus_path, file_path, source_doc):
    path = Path(file_path)
    extension = path.suffix.lower()
    metadata_keywords = infer_metadata_keywords(source_doc, path.name)
    return {
        "source_doc": source_doc,
        "file_name": path.name,
        "extension": extension,
        "relative_path": source_doc,
        "document_type": extension.lstrip(".") if extension else "",
        "metadata_keywords": metadata_keywords,
    }


def infer_metadata_keywords(relative_path, file_name):
    text = f"{relative_path} {file_name}".lower()
    keywords = []

    if any(term in text for term in ("git", "github", "commit", "commits")):
        keywords.extend(
            [
                "git",
                "github",
                "commit",
                "commits",
                "repository",
                "version control",
            ]
        )

    return " ".join(dict.fromkeys(keywords))
