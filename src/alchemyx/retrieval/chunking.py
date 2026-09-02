def chunk_text(text, chunk_size=300, overlap=50, min_chunk_size=20):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0:
        raise ValueError("overlap must be 0 or greater")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    if min_chunk_size < 0:
        raise ValueError("min_chunk_size must be 0 or greater")

    words = text.split()
    if not words:
        return []

    chunks = []
    ranges = []
    start = 0
    step = chunk_size - overlap

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]

        if len(chunk_words) >= min_chunk_size or start == 0:
            chunks.append(" ".join(chunk_words))
            ranges.append((start, end))
        else:
            previous_start, previous_end = ranges[-1]
            merge_start = max(previous_end, start)
            if merge_start < end:
                chunks[-1] = " ".join(words[previous_start:end])
                ranges[-1] = (previous_start, end)
            break

        if end == len(words):
            break

        start += step

    return chunks
