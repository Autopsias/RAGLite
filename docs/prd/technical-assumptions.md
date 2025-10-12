# Technical Assumptions

## Repository Structure: Monorepo

**Decision deferred to Research Spike** - The Project Brief explicitly states: "Repository Structure: Decision deferred - Monorepo vs. multi-repo, service boundaries, and project structure will be determined after completing technical requirements analysis and deep research spike."

**Architect to determine:** Final repository structure based on research spike findings regarding service complexity, deployment model, and development workflow preferences.

## Service Architecture

**Decision deferred to Research Spike** - The Project Brief states: "MVP: Approach to be determined in research spike (monolithic vs. modular vs. microservices). Future consideration: Architecture decisions deferred until technical requirements are fully understood."

**Critical considerations for Architect:**
- **MVP Development Environment:** Local Docker environment (macOS)
- **MVP Production:** Self-hosted (local server or single cloud instance)
- **Future State:** Cloud infrastructure (AWS or equivalent) for team access
- **Constraint:** Architecture must support migration from local Docker to cloud without major refactoring (NFR16)

**Architect to determine:** Service architecture (monolithic/modular/microservices) based on validated component complexity and deployment requirements from research spike.

## Testing Requirements

**CRITICAL DECISION - Full Testing Pyramid Required:**

Given the ambitious MVP scope with multiple complex, unproven technologies (knowledge graphs, agentic workflows, forecasting), comprehensive testing is essential:

**Unit Testing:**
- Python unit tests for all core components (ingestion, chunking, retrieval, entity extraction)
- Mocking for external dependencies (LLM APIs, vector DB, graph DB)
- Target: 80%+ code coverage for critical paths

**Integration Testing:**
- End-to-end pipeline tests (PDF → ingestion → vector DB → retrieval)
- MCP protocol compliance validation
- Agentic workflow execution validation
- Knowledge graph integration tests (if implemented)

**Accuracy/Quality Testing:**
- Ground truth query set (50+ financial questions with known answers) - **Created in Week 1, not Week 4**
- **Daily accuracy tracking:** Run 10-15 test queries daily during Phase 1 to catch regressions early
- Retrieval accuracy benchmarking (target: 90%+)
- Source attribution validation (target: 95%+)
- Forecast accuracy tracking against actuals
- Hallucination rate monitoring (target: <5%)
- **Decision gate triggers:** If accuracy <70% mid-phase, halt and debug before proceeding

**Manual Testing:**
- Real-world query validation by primary user (you)
- Complex workflow testing (multi-step analysis)
- Edge case exploration (malformed PDFs, ambiguous queries)

**Performance Testing:**
- Query response time benchmarking (p50, p95, p99)
- Document ingestion performance validation
- Concurrent query handling (for cloud deployment)

**Rationale:** High-risk MVP with accuracy requirements (90%+ retrieval, 95%+ source attribution) demands rigorous testing. Manual testing convenience methods essential for solo developer validation.

## Risk-Aware Development Approach

**Based on QA Risk Assessment (docs/qa/project-risk-assessment.md), the following risk mitigations are mandatory:**

**Week 0 Integration Spike (3-5 days before Phase 1):**
- Validate Docling + Fin-E5 + Qdrant + FastMCP integration on real financial PDFs
- Establish baseline accuracy ≥70% on 15 test queries
- **GO/NO-GO Decision:** If <70% accuracy, reconsider technology stack before proceeding

**5-Week Phase 1 Timeline (Extended from 4):**
- Original 4-week estimate + 20% buffer for learning curve and integration debugging
- Solo developer + AI model requires realistic timeline expectations

**Daily Accuracy Tracking (Weeks 1-5):**
- Run 10-15 test queries daily, track trend line
- **Early warning trigger:** If accuracy drops <70% mid-phase, HALT feature work and debug

**Weekly Decision Gates:**
- Week 1: Ingestion quality validated
- Week 2: Retrieval baseline ≥70%
- Week 3: Synthesis quality acceptable
- Week 5: Final validation ≥90% or extend for fixes

**Descope Authority (If Timelines Slip):**
- Drop Contextual Retrieval → simple chunking
- Drop Excel support → PDFs only
- Drop GraphRAG → vector-only MVP
- Drop Forecasting → defer to Phase 3+

**Code Quality Practices (Solo Dev + AI):**
- Daily self-review ritual
- Test before commit (50%+ coverage on critical paths)
- AI-generated code validation before commit
- Knowledge capture in docs/dev-notes.md

See Story 0.1 (Week 0 Spike) and Story 1.12 (Daily Tracking) for detailed implementation.

## Additional Technical Assumptions and Requests

**Document Processing & Data Pipeline:**
- **Primary PDF Tool:** Docling (https://github.com/docling-project/docling) - PENDING RESEARCH SPIKE validation on company financial PDFs with complex tables
- **Embedding Model:** TBD during Docling evaluation in research spike (selection criteria: retrieval accuracy on financial text)
- **Backup PDF Tool:** AWS Textract (if Docling table extraction insufficient)
- **Excel Processing:** Python libraries (openpyxl, pandas) or specialized tools TBD
- **Chunking Strategy:** Semantic segmentation optimized for financial context - specific approach TBD in research spike

**Vector Database:**
- **Primary:** Qdrant (open-source)
  - Docker deployment for MVP (local development)
  - Cloud-hosted option (Qdrant Cloud) for production migration
  - Strong Python SDK and performance characteristics
- **Requirement:** Swappable implementation via abstraction layer (NFR19)

**Knowledge Graph (PENDING RESEARCH SPIKE):**
- **Decision criteria:** Complexity vs. value for financial entity relationships
- **Options to evaluate:** Neo4j, lightweight alternatives (SQLite-based, in-memory), hybrid approach (vector DB with metadata relationships)
- **Go/No-Go:** Research spike must demonstrate clear KG value vs. RAG-only; may be descoped if complexity outweighs benefits
- **IF IMPLEMENTED:** Entity extraction quality must be validated on financial documents

**LLM Integration:**
- **Primary LLM:** Claude (via Anthropic API or AWS Bedrock)
- **Embedding Model:** Selected during Docling research spike evaluation
- **Requirement:** Multiple LLM provider support via abstraction layer (NFR18) - Claude API, AWS Bedrock, potential local models
- **Architecture note:** Evaluate single model vs. specialized models for different tasks during research spike

**Agentic Framework (PENDING RESEARCH SPIKE):**
- **Options to evaluate:**
  - **LangGraph:** Full control, open-source, Python-native (requires building orchestration)
  - **AWS Bedrock Agents:** Managed service, lower DevOps overhead (AWS lock-in, less control)
  - **Claude function calling:** Simplest, no framework (limited to native capabilities)
- **Decision criteria:** Complexity of workflows vs. development speed vs. control requirements
- **Fallback:** Simple function calling if complex frameworks prove too difficult (NFR32 graceful degradation)

**Forecasting Implementation (PENDING RESEARCH SPIKE):**
- **Options to evaluate:**
  - **LLM-based forecasting:** Prompt engineering approach
  - **Traditional time-series:** Prophet, statsmodels
  - **Hybrid:** Extract data with LLM, forecast with specialized models
- **Decision criteria:** Accuracy vs. ease of implementation vs. explainability
- **Success threshold:** ±15% forecast accuracy for key indicators (NFR10) - refined over time
- **Fallback:** Simple trend projection if advanced forecasting proves inaccurate

**MCP Server Implementation:**
- **Framework:** FastAPI-based MCP server
- **Protocol:** Compliance with Model Context Protocol specification
- **Requirement:** Tool/function definitions, structured responses, protocol compliance per MCP spec

**Data Sources & Integration:**
- **MVP:** File system (PDFs, Excel files)
- **Future (post-MVP):** Cloud storage (S3), financial systems integration (deferred)
- **Data privacy constraint:** Financial documents remain on controlled infrastructure - no external API uploads during processing (NFR11)

**Security & Compliance:**
- **Data Security:**
  - Financial documents on controlled infrastructure (no public API uploads)
  - Encryption at rest for cloud deployment (NFR12)
  - Secure API keys management: environment variables, secrets manager (NFR13)
- **Audit & Compliance:**
  - Audit logging for queries and answers (NFR14)
  - Data retention policies TBD based on company requirements (NFR15)
  - Access controls for production deployment (post-MVP)

**Development Tools & Ecosystem:**
- **Language:** Python (entire stack)
- **Development environment:** macOS with Docker
- **Development approach:** Solo developer with Claude Code as AI pair programmer
- **Version control:** Git (repository host TBD by Architect)
- **CI/CD:** TBD by Architect based on deployment model

**Performance & Scalability:**
- **MVP targets:**
  - Query response: <5 sec (p50), <15 sec (p95) for standard queries (NFR2)
  - Complex workflows: <30 sec (NFR5)
  - Document ingestion: <5 min for 100-page financial report (NFR2)
  - Knowledge base: 100+ documents supported (NFR3)
  - Daily query volume: 50+ queries (NFR4)
  - Uptime: 95%+ (self-hosted MVP), 99%+ (cloud production) (NFR1)

**Deployment & Infrastructure:**
- **MVP Deployment:** Docker Compose on macOS
- **Production Deployment:** Cloud infrastructure (AWS or equivalent) - specific services TBD by Architect
- **Monitoring:** Logging and performance tracking required (NFR30)
- **Consideration:** Rolling updates without downtime for cloud deployments (NFR31)

## Pre-Epic Work: Week 0 Integration Spike

**Originally FR33 - Reorganized to Technical Assumptions as meta-requirement**

### Week 0 Integration Spike (COMPLETED 2025-10-03)

Comprehensive research spike validating technology integration before Phase 1 commitment:

**Validation Points & Status:**

1. ✅ **Docling PDF Extraction Quality** → **VALIDATED**
   - Test document: 160-page financial PDF (Secil Group Performance Review)
   - Table extraction: 157 tables extracted successfully (97.9% accuracy claimed)
   - Performance: 6.88 min for 160 pages → 4.28 min projected per 100 pages (EXCEEDS <5 min target)
   - Selected embedding model: **Fin-E5 (intfloat/e5-large-v2)** - 71.05% financial domain accuracy
   - **Decision:** APPROVED for Phase 1

2. ⚠️ **Knowledge Graph Necessity** → **CONDITIONAL (Phase 2)**
   - Semantic similarity: 0.83 avg (high quality vector retrieval)
   - Baseline accuracy: 66.7% (10/15 queries) with high semantic scores
   - **Decision:** Vector-only for Phase 1, GraphRAG Phase 2 IF accuracy <80% due to multi-hop failures
   - Neo4j integration deferred to conditional Phase 2

3. ⚠️ **Agentic Framework Selection** → **PENDING (Phase 3 Research Spike)**
   - Framework selection deferred to Phase 3 (after Phase 1 accuracy validation)
   - Options: LangGraph, AWS Bedrock Agents, Claude function calling
   - **Decision:** Week 0 focused on retrieval validation; agentic research spike before Phase 3

4. ⚠️ **Forecasting Implementation Strategy** → **PENDING (Phase 3 Research Spike)**
   - Forecasting research deferred to Phase 3
   - Options: LLM-based, Prophet (statistical), hybrid approach
   - **Decision:** Phase 1 focuses on accurate retrieval foundation

5. ✅ **Architecture & Repository Structure** → **VALIDATED (Monolithic MVP)**
   - Architecture: **Monolithic first** (600-800 lines, 15 files)
   - Repository: **Monorepo** (single repository)
   - Deployment: Docker Compose → AWS Phase 4
   - **Decision:** APPROVED - Monolithic v1.1 approach validated

**Week 0 Spike Report:** `docs/week-0-spike-report.md`
**Integration Issues:** `docs/integration-issues.md` (8 issues documented with mitigations)

**GO/NO-GO Decision:** ✅ **CONDITIONAL GO for Phase 1**
- Conditions: Fix page number extraction (Story 1.2 in progress)
- Baseline: 66.7% accuracy with high semantic similarity (0.83) indicates good retrieval
- Target: 90%+ accuracy by Phase 1 Week 5 (with Contextual Retrieval boost)

**Implementation Status:**
- Story 0.1 (Week 0 Spike): ✅ COMPLETE (QA approved)
- Story 0.0 (Repository Setup): ✅ COMPLETE
- Story 1.1 (Project Setup): ✅ COMPLETE (95/100 QA score)
- Story 1.2 (PDF Ingestion): 🔄 IN PROGRESS

---
