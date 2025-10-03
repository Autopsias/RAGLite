"""Configuration settings for Week 0 Integration Spike."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
TEST_PDF_PATH = os.getenv(
    "TEST_PDF_PATH",
    str(PROJECT_ROOT / "docs" / "sample pdf" / "2025-08 Performance Review CONSO_v2.pdf")
)

# Qdrant Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "financial_docs")

# Embedding Model Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/e5-large-v2")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

# Chunking Configuration (per architecture: 500 words, 50 word overlap)
CHUNK_SIZE = 500  # words
CHUNK_OVERLAP = 50  # words

# MCP Server Configuration
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8000"))

# Search Configuration
DEFAULT_TOP_K = 5  # Number of results to return for similarity search
