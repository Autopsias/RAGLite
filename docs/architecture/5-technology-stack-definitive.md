# 5. Technology Stack (Definitive)

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **PDF Extraction** | Docling | Latest | Extract text/tables from PDFs | 97.9% table accuracy, DocLayNet-based |
| **Excel Processing** | openpyxl + pandas | Latest | Extract tabular data | Standard Python libraries |
| **Embedding Model** | Fin-E5 (finance-adapted) | Latest | Generate semantic vectors | 71.05% financial domain accuracy |
| **Chunking** | Contextual Retrieval | N/A | LLM-generated context per chunk | 98.1% retrieval accuracy |
| **Vector Database** | Qdrant | 1.11+ | Store/search embeddings | HNSW indexing, sub-5s retrieval |
| **Graph Database** | Neo4j | 5.x | Knowledge graph (Phase 2 conditional) | Cypher queries, managed cloud option |
| **MCP Server** | FastMCP (MCP Python SDK) | 1.x | Expose tools via MCP protocol | Official SDK, 19k GitHub stars |
| **LLM (Primary)** | Claude 3.7 Sonnet | via API | Reasoning, analysis, synthesis | State-of-art reasoning, 200K context |
| **Forecasting** | Prophet | 1.1+ | Time-series baseline | Facebook library, seasonal handling |
| **Backend Language** | Python | 3.11+ | All application code | RAG ecosystem standard, async support |
| **API Framework** | FastAPI | 0.115+ (optional) | REST endpoints if needed | High performance, async native |
| **Document Storage** | S3 (cloud) / Local FS (dev) | N/A | Store ingested documents | Scalable, versioning, encryption |
| **Secrets** | AWS Secrets Manager / .env | N/A | API keys, credentials | Secure, rotatable |
| **Containerization** | Docker + Docker Compose | Latest | Local development | Service isolation, reproducible |
| **Cloud Platform** | AWS | N/A | Production deployment (Phase 4) | ECS/Fargate, managed services |
| **IaC** | Terraform | Latest | Infrastructure as Code (Phase 4) | Version-controlled infrastructure |
| **CI/CD** | GitHub Actions | N/A | Testing and deployment | Git-integrated |
| **Monitoring** | CloudWatch + Prometheus | N/A | Performance tracking (Phase 4) | AWS native + open-source |
| **Logging** | Structured JSON | N/A | Application logs, audit trail | CloudWatch-compatible |
| **Testing** | pytest + pytest-asyncio | Latest | Python unit/integration tests | Standard testing stack |

---
