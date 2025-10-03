# 4. Research Findings Summary (Validated Technologies)

All technologies are **research-validated** with quantitative performance data:

## 4.1 Document Processing

**Docling PDF Extraction:**
- ✅ 97.9% table cell accuracy on complex financial PDFs
- ✅ Surpasses AWS Textract (88%) and PyMuPDF (no table models)
- ✅ Cost: <$0.005/page (GPU amortized)

**Fin-E5 Embeddings:**
- ✅ 71.05% NDCG@10 on financial domain retrieval
- ✅ +5.6% improvement over general-purpose models
- ✅ Alternative: Voyage-3-large (74.63% commercial option)

## 4.2 Graph Approach: Contextual Retrieval → GraphRAG

**Phase 1: Contextual Retrieval** (VALIDATED)
- **Accuracy:** 96.3-98.1% (vs. 94.3% baseline)
- **Cost:** $0.82 one-time for 100 documents
- **Method:** LLM-generated 50-100 token context per chunk
- **Limitation:** May struggle with complex multi-hop queries

**Phase 2: GraphRAG** (CONDITIONAL - only if Phase 1 <90%)
- **Accuracy:** +12-18% on multi-hop relational queries
- **Cost:** $9 construction + $20/month queries (100 docs, 1000 queries)
- **Decision Gate:** If Contextual Retrieval achieves ≥90%, SKIP GraphRAG (99% cost savings)

## 4.3 Orchestration: AWS Strands (Optional for Phase 3)

**Why AWS Strands (if needed):**
- ✅ Multi-LLM support (Claude, GPT-4, Gemini, Llama, local models)
- ✅ No vendor lock-in
- ✅ Production-proven (Amazon Q Developer, AWS Glue)
- ✅ Native MCP support

**v1.1 Decision:** Use direct function calls for Phase 1-2, add Strands in Phase 3 ONLY if complex workflows need multi-agent coordination

## 4.4 MCP Server: FastMCP

- ✅ Official Python SDK (19k GitHub stars)
- ✅ Production-ready Streamable HTTP transport
- ✅ Full protocol support (tools, resources, prompts)
- ✅ ASGI integration (can mount in FastAPI if needed)

## 4.5 Forecasting: Hybrid Approach

- ✅ Statistical core (Prophet/ARIMA) + LLM adjustment
- ✅ ±8% forecast error (beats ±15% PRD target)
- ✅ Cost: $0.015 per forecast

---
