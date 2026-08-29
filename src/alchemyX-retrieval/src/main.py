import os

from dotenv import find_dotenv, load_dotenv
from retrieval import RetrievalPipeline

load_dotenv(find_dotenv())

API_KEY = os.getenv("VOYAGE_API_KEY")
if not API_KEY:
    raise RuntimeError("VOYAGE_API_KEY is missing. Add it to the .env file.")

# Set up the pipeline
pipeline = RetrievalPipeline(api_key=API_KEY)

# Add a test document
sample_doc = """
Ser Caldrin Vale was a Veyran knight and diplomatic envoy active during the late Toll Wars period. 
Born to a minor riverland house, Caldrin entered service under the merchant-princes of Lumenford 
after losing his family estate to debt. Caldrin is chiefly remembered for his role in the Night of 
Falling Bells, a failed winter parley held at Thornwatch. He was assigned to escort Mira Quen, a 
Lumenford courier with informal ties to canal smugglers, to the monastery-fortress.
"""

pipeline.add_document(doc_id="caldrin_wiki", text=sample_doc, chunk_size=30, overlap=5)

# Query it
results = pipeline.query("Who did Caldrin escort to Thornwatch?")
print(results["documents"])
print(results["metadatas"])
