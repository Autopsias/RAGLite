# Epic 1: Foundation & Accurate Retrieval

**Epic Goal:** Deliver a working conversational financial Q&A system with 90%+ retrieval accuracy that enables users to ask natural language questions via MCP and receive accurate, source-attributed answers from company financial documents.

**⚠️ RISK MITIGATION: Epic 1 includes Week 0 Integration Spike (Story 0.1) to validate technology stack before committing to 5-week Phase 1 development. See Story 0.1 for mandatory go/no-go criteria.**

## Story 0.1: Week 0 Integration Spike (MANDATORY PRE-PHASE 1)

**As a** developer,
**I want** to validate end-to-end technology integration on real financial documents BEFORE starting Phase 1,
**so that** I can identify showstopper issues early and establish accuracy baseline.

**Duration:** 3-5 days
**Priority:** CRITICAL - Blocks all Phase 1 work

**Acceptance Criteria:**
1. Ingest 1 real company financial PDF (100+ pages) with Docling
2. Generate embeddings with Fin-E5 model
3. Store vectors in Qdrant via Docker Compose
4. Implement basic MCP server (FastMCP) exposing query tool
5. Create 15 ground truth Q&A pairs from test document
6. Measure baseline retrieval accuracy (vector search only, no LLM synthesis)
7. Document integration issues, API quirks, version conflicts discovered
8. Establish performance baseline (ingestion time, query latency)

**Success Criteria (GO/NO-GO for Phase 1):**
- ✅ **GO:** Baseline retrieval accuracy ≥70% (10+ out of 15 queries return relevant chunks)
- ✅ **GO:** End-to-end pipeline functional (PDF → Docling → Fin-E5 → Qdrant → FastMCP)
- ✅ **GO:** No major integration blockers requiring >2 days to resolve
- ⚠️ **REASSESS:** Accuracy 50-69% → Investigate root cause, may need chunking/embedding adjustments
- 🛑 **NO-GO:** Accuracy <50% → Technology stack unsuitable, consider alternatives (AWS Textract, different embeddings)

**Deliverables:**
- Working integration spike codebase (throwaway prototype, not production)
- Week 0 Spike Report documenting: accuracy baseline, integration issues, recommendations
- Updated Phase 1 plan based on learnings

**Rationale:** Risk assessment (RISK-001, RISK-002) identifies high probability of integration failures and accuracy shortfalls. Week 0 validation de-risks Phase 1 by surfacing issues early when pivoting is cheap.

## Story 0.2: API Account & Cloud Infrastructure Setup (MANDATORY PRE-PHASE 1)

**As a** user,
**I want** all required third-party API accounts and cloud infrastructure configured BEFORE development begins,
**so that** development is not blocked by account provisioning delays or missing credentials.

**Duration:** 1-2 days (account approval may cause delays)
**Priority:** CRITICAL - Blocks all Phase 1 work
**Assignment:** USER (human-only task - requires payment information, company email verification, terms acceptance)

**Acceptance Criteria:**
1. **Anthropic Claude API Account:**
   - Account created at console.anthropic.com
   - API key generated and securely stored
   - Usage limits reviewed (ensure sufficient for MVP development: ~1M tokens estimated)
   - Billing configured (credit card or payment method on file)
   - API key added to `.env.example` template as placeholder: `ANTHROPIC_API_KEY=your_key_here`

2. **AWS Account (Conditional - if using Bedrock or cloud deployment):**
   - AWS account created or existing account identified
   - IAM user created with appropriate permissions (Bedrock access if using, ECS/S3 if deploying)
   - Access keys generated (Access Key ID and Secret Access Key)
   - AWS credentials stored securely (not in repository)
   - AWS CLI configured locally for development/deployment

3. **Qdrant Cloud Account (for Production Deployment - Epic 5):**
   - Qdrant Cloud account created at cloud.qdrant.io
   - Free tier or paid plan selected based on MVP requirements
   - API key generated for cloud instance access
   - Note: Local Qdrant via Docker Compose for MVP development (Epic 1-4)

4. **Secrets Management Setup:**
   - `.env.example` template created with all required API key placeholders
   - `.env` added to `.gitignore` (prevent credential leakage)
   - Documentation includes instructions for developers to create local `.env` from template
   - For cloud deployment: AWS Secrets Manager or equivalent identified for production

5. **Cost Monitoring Setup:**
   - Anthropic Claude API usage alerts configured (notify at 50%, 75%, 90% of budget)
   - AWS billing alerts configured if using AWS services
   - Budget defined: Estimated $200-500 for MVP development phase (verify sufficiency)

**Success Criteria:**
- ✅ All API keys generated and accessible (verified by test API call)
- ✅ No credential exposure in version control (`.env` gitignored, `.env.example` has placeholders only)
- ✅ Documentation complete for other developers to replicate setup
- ✅ Billing/budget alerts active to prevent surprise costs

**Deliverables:**
- `.env.example` file with all API key placeholders documented
- `docs/api-setup-guide.md` documenting account creation steps and credential management
- Active API accounts with valid credentials ready for Story 1.1

**Rationale:** External API accounts often have 24-48 hour approval delays (especially AWS). Creating accounts BEFORE development ensures no blocking delays during Phase 1. This is a human-only task requiring payment methods and email verification that cannot be automated.

**Dependencies:** None (can run in parallel with Story 0.1 Week 0 Spike)

## Story 1.1: Project Setup & Development Environment

**As a** developer,
**I want** a configured development environment with all necessary tools and dependencies,
**so that** I can begin implementation immediately without setup friction.

**Acceptance Criteria:**
1. Python virtual environment created with dependencies managed via requirements.txt or poetry
2. Git repository initialized with .gitignore configured for Python, secrets, and IDE files
3. Docker and Docker Compose installed and validated on macOS development machine
4. Project directory structure established per Architect's design
5. Environment variables template (.env.example) created for API keys and configuration
6. README.md includes setup instructions, architecture overview, and development workflow
7. Pre-commit hooks configured for code formatting (black, isort) and linting (flake8/ruff)

## Story 1.2: PDF Document Ingestion with Docling

**As a** system,
**I want** to ingest financial PDF documents and extract text, tables, and structure accurately,
**so that** financial data is available for retrieval and analysis.

**Acceptance Criteria:**
1. Docling library integrated and configured per Architect's specifications
2. PDF ingestion pipeline accepts file path and extracts text content with 95%+ accuracy
3. Financial tables extracted with structure preserved (rows, columns, headers, merged cells)
4. Document metadata captured (filename, ingestion timestamp, document type if detectable)
5. Ingestion errors logged with clear error messages for malformed or corrupted PDFs
6. Successfully ingests sample company financial PDFs provided for testing
7. Ingestion performance meets <5 minutes for 100-page financial report (NFR2)
8. Unit tests cover ingestion pipeline with mocked Docling responses
9. Integration test validates end-to-end PDF ingestion with real sample document

## Story 1.3: Excel Document Ingestion

**As a** system,
**I want** to ingest Excel spreadsheets and extract tabular financial data,
**so that** financial data from Excel files is available alongside PDF content.

**Acceptance Criteria:**
1. Excel parsing library integrated (openpyxl, pandas, or Architect-specified tool)
2. Excel ingestion pipeline accepts file path and extracts sheet data preserving formulas and relationships
3. Multi-sheet workbooks handled with sheet names preserved as metadata
4. Numeric formatting preserved (currencies, percentages, dates)
5. Successfully ingests sample company Excel financial files
6. Errors handled gracefully for password-protected or corrupted files
7. Unit tests cover Excel parsing logic
8. Integration test validates end-to-end Excel ingestion

## Story 1.4: Document Chunking & Semantic Segmentation

**As a** system,
**I want** to chunk ingested documents using semantic segmentation optimized for financial context,
**so that** retrieval returns relevant, complete information without context fragmentation.

**Acceptance Criteria:**
1. Chunking strategy implemented per Architect's specification (size, overlap, semantic boundaries)
2. Financial context preserved across chunks (tables not split mid-row, sections kept together)
3. Chunk metadata includes source document, page number, section heading where applicable
4. Chunking handles both narrative text and structured tables appropriately
5. Chunk quality validated manually on sample documents (no mid-sentence splits, logical boundaries)
6. Unit tests cover chunking logic with various document structures
7. Performance acceptable for 100-page documents (<30 seconds chunking time)

## Story 1.5: Embedding Model Integration & Vector Generation

**As a** system,
**I want** to generate vector embeddings for document chunks using the Architect-selected embedding model,
**so that** semantic similarity search is possible for retrieval.

**Acceptance Criteria:**
1. Embedding model integrated per Architect's selection from research spike
2. Vector embeddings generated for all document chunks
3. Embedding generation handles batch processing for efficiency
4. Embeddings cached to avoid redundant computation on re-ingestion
5. API rate limiting respected if using external embedding service
6. Unit tests cover embedding generation with mocked model responses
7. Integration test validates embeddings generated for sample document chunks

## Story 1.6: Qdrant Vector Database Setup & Storage

**As a** system,
**I want** to store document chunk embeddings in Qdrant vector database with efficient indexing,
**so that** sub-5 second semantic search retrieval is possible.

**Acceptance Criteria:**
1. Qdrant deployed via Docker Compose in local development environment
2. Collection created with appropriate vector dimensions and distance metric per Architect's specification
3. Document chunks and embeddings stored with metadata (document name, page, section)
4. Indexing configured for optimal retrieval performance (HNSW or IVF per Architect)
5. Storage handles 100+ documents without performance degradation (NFR3)
6. Connection management and error handling implemented (retries, connection pooling)
7. Unit tests cover Qdrant client operations with mocked database
8. Integration test validates storage and retrieval from actual Qdrant instance

## Story 1.7: Vector Similarity Search & Retrieval

**As a** system,
**I want** to perform vector similarity search and retrieve relevant document chunks for user queries,
**so that** accurate financial information can be surfaced conversationally.

**Acceptance Criteria:**
1. Query embedding generation using same model as document embeddings
2. Similarity search returns top-k relevant chunks (k configurable, default per Architect)
3. Retrieval performance <5 seconds (p50) for standard queries (NFR13)
4. Filtering by metadata supported (date range, document type) if specified in query
5. Relevance scoring included in results for downstream ranking
6. Unit tests cover retrieval logic with mocked vector search
7. Integration test validates end-to-end retrieval accuracy on ground truth query set
8. Retrieval accuracy measured and documented (target: 90%+ on test set per NFR6)

## Story 1.8: Source Attribution & Citation Generation

**As a** system,
**I want** to provide verifiable source citations for all retrieved information,
**so that** users can validate answers against original financial documents.

**Acceptance Criteria:**
1. Each retrieved chunk includes source metadata (document name, page number, section heading)
2. Citation format clearly identifies source: "(Source: Q3_Report.pdf, page 12, Revenue section)"
3. Source attribution accuracy 95%+ validated on test queries (NFR7)
4. Multiple sources cited when answer synthesizes information from multiple chunks
5. Citations included in final response format for MCP client display
6. Unit tests validate citation generation from metadata
7. Manual validation confirms citations point to correct document locations

## Story 1.9: MCP Server Foundation & Protocol Compliance

**As a** system,
**I want** to expose RAGLite capabilities via Model Context Protocol server,
**so that** Claude Desktop and other MCP clients can interact with the financial knowledge base.

**Acceptance Criteria:**
1. FastAPI-based MCP server implemented per Architect's design
2. MCP protocol compliance validated (server initialization, tool discovery, tool execution)
3. Health check endpoint responds with server status
4. Error handling returns proper MCP error responses
5. Server starts successfully via Docker Compose
6. Integration test validates MCP client can connect and discover tools
7. Server logs requests and responses for debugging

## Story 1.10: Natural Language Query Tool (MCP)

**As a** user,
**I want** to ask natural language financial questions via MCP client,
**so that** I can access financial knowledge conversationally without learning query syntax.

**Acceptance Criteria:**
1. MCP tool defined: "query_financial_documents" with natural language query parameter
2. Tool receives query, generates embedding, performs retrieval, synthesizes answer
3. Response includes synthesized answer and source citations
4. Query understanding handles financial terminology correctly
5. Response format optimized for conversational display in MCP client
6. Tool tested via Claude Desktop or MCP-compatible test client
7. End-to-end test: Ask question → Receive accurate answer with citation
8. 10+ sample queries from ground truth test set validated for accuracy

## Story 1.11: Answer Synthesis & Response Generation

**As a** system,
**I want** to synthesize coherent answers from retrieved chunks using LLM,
**so that** users receive natural language answers instead of raw document fragments.

**Acceptance Criteria:**
1. LLM integration (Claude API or Bedrock) per Architect's specification
2. Prompt engineering incorporates retrieved chunks with instruction to synthesize answer
3. Prompt includes instruction to cite sources and avoid hallucination
4. Response generated in <5 seconds for standard queries (NFR13)
5. Hallucination rate <5% validated on test queries (NFR8)
6. Answer quality manually validated on sample queries (coherent, accurate, properly cited)
7. Error handling for LLM API failures (retries, fallback messaging)
8. Unit tests cover prompt construction and response parsing

## Story 1.12: Ground Truth Test Set Validation & Continuous Accuracy Tracking

**As a** developer,
**I want** to validate retrieval accuracy against a ground truth test set of financial queries with daily tracking,
**so that** I can measure and improve system performance objectively and catch accuracy regressions early.

**Acceptance Criteria:**
1. Ground truth test set created **in Week 1** (not Week 4) with 50+ representative financial queries and known correct answers
2. Automated test suite runs all queries and compares results to expected answers
3. Retrieval accuracy measured: % of queries returning correct information (target: 90%+ per NFR6)
4. Source attribution accuracy measured: % of citations pointing to correct documents (target: 95%+ per NFR7)
5. Performance metrics captured (p50, p95 response times)
6. Test results documented with failure analysis for inaccurate queries
7. Test suite executable via CLI command for continuous validation
8. **RISK MITIGATION:** Daily accuracy tracking during Weeks 1-4:
   - Run subset of 10-15 test queries daily against work-in-progress system
   - Track accuracy trend line (should improve as components mature)
   - **Early warning trigger:** If accuracy drops below 70% mid-phase, HALT feature work and debug root cause
9. Weekly accuracy review with decision gate:
   - Week 1 end: Ingestion quality validated (Docling extraction accurate?)
   - Week 2 end: Retrieval baseline ≥70% (chunking/embeddings working?)
   - Week 3 end: Synthesis quality good (LLM prompts effective?)
   - Week 4 end: Final validation ≥90% or extend to Week 5 for fixes

---
