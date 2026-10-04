"""Central configuration for PocketFriend.

Every tunable value lives here so nothing is hard-coded across the app.
Values can be overridden with environment variables, which keeps the
configuration reproducible and hackathon-demo friendly.
"""

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
CHROMA_DIR = DATA_DIR / "chroma"
DEMO_DIR = DATA_DIR / "demo"
DB_PATH = DATA_DIR / "pocketfriend.db"

# Chroma requires a single collection name for the whole app.
CHROMA_COLLECTION = "pocketfriend_documents"


def ensure_directories() -> None:
    """Create the local storage folders if they do not exist yet."""
    for folder in (DATA_DIR, DOCUMENTS_DIR, CHROMA_DIR, DEMO_DIR):
        folder.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Local AI (Ollama + Gemma)
# --------------------------------------------------------------------------

# The default open-weight model. Change with the POCKETFRIEND_MODEL env var,
# e.g. POCKETFRIEND_MODEL=gemma3:4b
OLLAMA_MODEL = os.getenv("POCKETFRIEND_MODEL", "gemma3:1b")

# Ollama host. Defaults to the local server, never a cloud endpoint.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Seconds to wait for Ollama before giving up with a friendly message.
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))

# Upper bound on generated tokens. gemma3:1b is small, so short answers win.
MAX_TOKENS = int(os.getenv("POCKETFRIEND_MAX_TOKENS", "900"))

# Temperature. Low values keep a 1B model factual and literal.
TEMPERATURE = float(os.getenv("POCKETFRIEND_TEMPERATURE", "0.2"))

# --------------------------------------------------------------------------
# Embeddings / retrieval
# --------------------------------------------------------------------------

# Small English sentence-embedding model (~90 MB, fast on an 8 GB machine).
EMBEDDING_MODEL = os.getenv(
    "POCKETFRIEND_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)

# Roughly 900 characters keeps chunks inside MiniLM's token window with room
# to spare, and keeps citations precise (small chunks = accurate pages).
CHUNK_SIZE = int(os.getenv("POCKETCHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("POCKETCHUNK_OVERLAP", "150"))

# How many chunks to retrieve per question.
TOP_K = int(os.getenv("POCKETFRIEND_TOP_K", "5"))

# Cosine similarity threshold, calibrated against the demo material: real
# questions scored 0.25+, off-topic questions 0.18 and below. Sitting just above
# the gap means PocketFriend refuses rather than guesses.
RELEVANCE_THRESHOLD = float(os.getenv("POCKETFRIEND_RELEVANCE", "0.22"))

# --------------------------------------------------------------------------
# Product constants
# --------------------------------------------------------------------------

APP_TITLE = "PocketFriend"
APP_TAGLINE = "A private AI study companion that knows your documents."

PRIORITIES = ["high", "medium", "low"]
DIFFICULTIES = ["Easy", "Medium", "Hard"]

# Study plans longer than this are trimmed so a 1B model stays coherent.
MAX_PLAN_DAYS = 14