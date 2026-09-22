import os
import shutil
from pathlib import Path

from dotenv import load_dotenv


# Load one project-root configuration file for every application entry point.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if PROJECT_ROOT.name == "src":
    PROJECT_ROOT = PROJECT_ROOT.parent
load_dotenv(PROJECT_ROOT / ".env")

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "minimax/minimax-m3:free"
OPENROUTER_FALLBACK_MODELS = "openrouter/free"

VOYAGE_MODEL = "voyage-4-lite"
RERANK_MODEL = "rerank-2.5"

RRF_K = 60
RETRIEVAL_TOP_K = 5
RERANK_CANDIDATES = 40
MIN_RERANK_SCORE = 0.5
MAX_AGENT_ITERATIONS = 4
EMBEDDING_BATCH_SIZE = 1000
DEFAULT_CHUNK_SIZE = 120
DEFAULT_CHUNK_OVERLAP = 40

DEFAULT_COLLECTION_NAME = "alchemyx_docs"
DEFAULT_CHROMA_DIRECTORY = "data/chroma"
DEFAULT_BM25_PATH = "data/bm25.json"
DEFAULT_DOCUMENT_REGISTRY_PATH = "data/document_registry.json"
DEFAULT_CORPUS_PATH = os.getenv("ALCHEMYX_CORPUS_PATH", "Ashen_Era_Archive")
TESSERACT_CMD = os.getenv("TESSERACT_CMD") or shutil.which("tesseract") or (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe" if os.name == "nt" else "tesseract"
)
VOYAGE_MAX_RETRIES = 3
VOYAGE_RETRY_BASE_SECONDS = 1.0
