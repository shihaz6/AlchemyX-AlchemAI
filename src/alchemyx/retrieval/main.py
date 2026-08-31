import os
from dotenv import find_dotenv, load_dotenv
from retrieval import RetrievalPipeline

load_dotenv(find_dotenv())
API_KEY = os.getenv("VOYAGE_API_KEY")
if not API_KEY:
    raise RuntimeError("VOYAGE_API_KEY is missing. Add it to the .env file.")

pipeline = RetrievalPipeline(api_key=API_KEY)

caldrin_doc = """
Ser Caldrin Vale was a Veyran knight and diplomatic envoy active during the late Toll Wars period. 
Born to a minor riverland house, Caldrin entered service under the merchant-princes of Lumenford 
after losing his family estate to debt. Caldrin is chiefly remembered for his role in the Night of 
Falling Bells, a failed winter parley held at Thornwatch. He was assigned to escort Mira Quen, a 
Lumenford courier with informal ties to canal smugglers, to the monastery-fortress.
"""

mira_doc = """
Mira Quen was a canal-singer and smuggler from the glass-market city of Lumenford. 
She disappeared on the Night of Falling Bells with a sealed reliquary, and Abbess 
Ilyra Senn later claimed she had asked Mira to remove it before Thornwatch's council 
could hand it to the Iron Prior.
"""

pipeline.add_document(doc_id="caldrin_wiki", text=caldrin_doc, chunk_size=30, overlap=5)
pipeline.add_document(doc_id="mira_wiki", text=mira_doc, chunk_size=30, overlap=5)

# This should pull from mira_wiki
print("\n--- Query: Why did Mira take the reliquary? ---")
results = pipeline.query("Why did Mira take the reliquary?")
for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
    print(f"[{meta['source_doc']}] dist={dist:.4f} → {doc[:80]}...")

# This should pull from caldrin_wiki
print("\n--- Query: Who did Caldrin escort? ---")
results = pipeline.query("Who did Caldrin escort?")
for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
    print(f"[{meta['source_doc']}] dist={dist:.4f} → {doc[:80]}...")


print("\n--- Query: What is the time now? ---")
results = pipeline.query("What is the time now?")
for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
    print(f"[{meta['source_doc']}] dist={dist:.4f} → {doc[:80]}...")