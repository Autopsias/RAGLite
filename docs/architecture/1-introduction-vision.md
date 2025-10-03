# 1. Introduction & Vision

## Purpose

RAGLite is an **AI-powered financial intelligence platform** enabling natural language access to company financial documents through Retrieval-Augmented Generation (RAG).

**v1.1 Architecture Goals:**
- ✅ Achieve 90%+ retrieval accuracy with validated technologies
- ✅ Deliver working MVP in 4-5 weeks (solo developer + Claude Code)
- ✅ Start simple (monolithic), evolve to microservices ONLY if scaling requires
- ✅ Minimize vendor lock-in while using production-proven technologies
- ✅ Support local Docker development → AWS deployment path

## Scope (v1.1 MVP)

**In Scope:**
- Single monolithic MCP server (FastMCP)
- PDF ingestion with Docling (97.9% table accuracy)
- Vector search with Qdrant + Fin-E5 embeddings
- LLM synthesis with Claude 3.7 Sonnet
- Source attribution (document, page, section)
- Contextual Retrieval chunking (98.1% accuracy)
- Optional GraphRAG (Phase 2 - only if accuracy <90%)
- Forecasting & Insights (Phase 3)

**Out of Scope (MVP):**
- Custom frontend UI (users interact via MCP clients: Claude Code, Claude Desktop)
- Microservices architecture (deferred to Phase 4 if needed)
- Real-time collaboration (Phase 5+)
- Multi-tenant architecture (single user MVP)

## Architectural Principles

1. **Simplicity First** - Start with simplest solution that meets requirements
2. **Validated Technologies** - Use research-proven technologies (Docling, Fin-E5, etc.)
3. **Phased Complexity** - Add complexity ONLY when simpler approaches fail
4. **Evolution Over Perfection** - Ship functional MVP, iterate based on real usage
5. **AI-Agent Friendly** - Clear patterns for Claude Code to implement

---
