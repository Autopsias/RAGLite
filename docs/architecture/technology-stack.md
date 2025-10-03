# Technology Stack

## Definitive Technology Selection

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **PDF Extraction** | Docling | Latest | Extract text, tables, structure from PDFs | 97.9% table accuracy, DocLayNet-based, surpasses Textract |
| **Excel Processing** | openpyxl + pandas | Latest | Extract tabular data from Excel | Standard Python libraries, formula preservation |
| **Embedding Model** | Fin-E5 (finance-adapted e5-mistral-7b) | Latest | Generate semantic vectors for financial text | 71.05% financial domain NDCG@10, +5.6% vs general models |
| **Chunking Strategy** | Contextual Retrieval | N/A | LLM-generated 50-100 token context per chunk | 98.1% retrieval accuracy, $1.02/M tokens preprocessing |
| **Vector Database** | Qdrant | 1.11+ | Store and search document embeddings | HNSW indexing, sub-5s retrieval, Docker-friendly, swappable |
| **Graph Database** | Neo4j | 5.x | Store knowledge graph (Phase 2) | Cypher queries, Agentic GraphRAG support, managed cloud option |
| **MCP Server Framework** | MCP Python SDK (FastMCP) | 1.x | Expose microservices via MCP protocol | Official SDK, 19k stars, Streamable HTTP, production-ready |
| **Orchestration** | **AWS Strands** | 1.x | Multi-agent workflow coordination | Multi-LLM support, no vendor lock-in, Amazon Q proven |
| **LLM (Primary)** | Claude 3.7 Sonnet | via Bedrock | Reasoning, analysis, contextualization | State-of-art reasoning, 200K context, financial domain strong |
| **LLM (Alternative)** | GPT-4.1, Gemini 2.0 | via APIs | LLM flexibility testing | AWS Strands enables easy model swapping |
| **Forecasting (Statistical)** | Prophet | 1.1+ | Time-series baseline forecasting | Facebook's library, handles seasonality, easy integration |
| **Forecasting (LLM)** | Claude API | N/A | Forecast adjustment and context | LLM-based residual correction for ±8% accuracy |
| **Backend Language** | Python | 3.11+ | All microservices implementation | RAG ecosystem standard, AI/ML library support, async support |
| **API Framework** | FastAPI | 0.115+ | REST endpoints (if needed), ASGI support | High performance, async native, OpenAPI auto-docs |
| **Document Storage** | S3 (cloud) / Local FS (dev) | N/A | Store ingested documents and artifacts | Scalable, versioning, encryption at rest |
| **Secrets Management** | AWS Secrets Manager (cloud) / .env (dev) | N/A | API keys, credentials | Secure, rotatable, audit-logged |
| **Containerization** | Docker + Docker Compose | Latest | Local development environment | Service isolation, reproducible environments |
| **Cloud Platform** | AWS | N/A | Production deployment | ECS/EKS, managed Qdrant/OpenSearch, Bedrock integration |
| **IaC Tool** | Terraform (or CDK) | Latest | Infrastructure as Code | Version-controlled infrastructure, AWS native |
| **CI/CD** | GitHub Actions | N/A | Automated testing and deployment | Git-integrated, Docker support, AWS deployment |
| **Monitoring** | CloudWatch + Prometheus | N/A | Performance tracking, alerting | AWS native + open-source metrics |
| **Logging** | CloudWatch Logs + Structured JSON | N/A | Application logs, query audit trail | Centralized, queryable, compliant (NFR14) |
| **Testing (Unit)** | pytest | Latest | Python unit tests (80%+ coverage target) | Standard Python testing, mocking support |
| **Testing (Integration)** | pytest + Docker | Latest | End-to-end pipeline tests | Docker test containers, real service integration |
| **Testing (Accuracy)** | Custom test harness | N/A | Ground truth query validation (50+ queries) | Measure 90%+ retrieval, 95%+ attribution accuracy |

---
