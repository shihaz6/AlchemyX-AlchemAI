def chunk_text(text, chunk_size=300, overlap=50, min_chunk_size=20):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        if len(chunk_words) >= min_chunk_size or start == 0:
            # keep it if it's long enough, or if it's the only chunk we have
            chunks.append(" ".join(chunk_words))
        else:
            # too small — merge into the previous chunk instead of keeping it separate
            chunks[-1] = chunks[-1] + " " + " ".join(chunk_words)
        start += chunk_size - overlap
    return chunks

if __name__ == "__main__":
    sample_doc = """
Ser Caldrin Vale was a Veyran knight and diplomatic envoy active during the late Toll Wars period. 
Born to a minor riverland house, Caldrin entered service under the merchant-princes of Lumenford 
after losing his family estate to debt. Caldrin is chiefly remembered for his role in the Night of 
Falling Bells, a failed winter parley held at Thornwatch. He was assigned to escort Mira Quen, a 
Lumenford courier with informal ties to canal smugglers, to the monastery-fortress.
"""
    chunks = chunk_text(sample_doc, chunk_size=30, overlap=5)
    for i, c in enumerate(chunks):
        print(f"---Chunk{i} ---")
        print(c)
        print()
