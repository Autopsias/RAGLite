# Research Findings Summary

## Validated Technologies

The architecture is based on **4 comprehensive deep research reports** validating all critical technologies:

### 1. Document Processing & Retrieval

**Docling PDF Extraction:**
- 97.9% table cell accuracy on complex financial PDFs
- Surpasses AWS Textract (88%) and PyMuPDF (no table models)
- Cost: <$0.005/page (GPU amortized)

**Fin-E5 Embeddings:**
- 71.05% NDCG@10 on financial domain retrieval
- +5.6% improvement over general-purpose models
- Alternative: Voyage-3-large (74.63% commercial)

### 2. Graph Approach: Contextual Retrieval → GraphRAG

**Phase 1: Anthropic Contextual Retrieval** (VALIDATED)
- **Accuracy:** 96.3-98.1% (vs. 94.3% baseline)
- **Cost:** $0.82 one-time for 100 documents
- **Method:** LLM-generated 50-100 token context per chunk
- **Limitation:** Limited multi-hop reasoning capability

**Phase 2: Agentic GraphRAG** (CONDITIONAL - only if Phase 1 <95%)
- **Accuracy:** +12-18% on multi-hop queries
- **Cost:** $9 construction + $20/month queries (100 docs, 1000 queries)
- **Implementation:** Microsoft Research approach (community detection + agent navigation)

**Decision Gate:** If Contextual Retrieval achieves 95%+ accuracy on multi-hop queries, **skip GraphRAG entirely** (99% cost savings)

### 3. Orchestration: AWS Strands (Not Claude Agent SDK)

**Why AWS Strands:**
- ✅ **Multi-LLM support:** Claude, GPT-4, Gemini, Llama, Ollama, local models
- ✅ **No vendor lock-in:** Can switch LLM providers without code changes
- ✅ **Production-proven:** Amazon Q Developer, AWS Glue, VPC Reachability Analyzer
- ✅ **Native MCP support:** Built-in MCP client for tool integration
- ✅ **150K+ PyPI downloads:** Established community

**Comparison:**

| Feature | AWS Strands | Claude Agent SDK | LangGraph |
|---------|-------------|------------------|-----------|
| **Multi-LLM** | ✅ 10+ providers | ⚠️ Claude/Bedrock/Vertex | ✅ Any via API |
| **Vendor Lock-in** | **LOW** | MEDIUM | LOW |
| **Production Use** | Amazon Q, Glue | Claude Code | Widespread |
| **MCP Native** | ✅ Yes | ✅ Yes | ⚠️ Adapters |

### 4. MCP Server: FastMCP (Official Python SDK)

- **Official reference implementation** (19k GitHub stars)
- **Production-ready transports:** Streamable HTTP for scalability
- **Full protocol support:** Tools, resources, prompts, OAuth 2.1
- **ASGI integration:** Can mount into FastAPI if needed

### 5. Forecasting: Hybrid Approach

- **Statistical core** (Prophet/ARIMA) + **LLM adjustment**
- **±8% forecast error** (beats ±15% PRD target)
- **Cost:** $0.015 per forecast

## Cost Analysis (Year 1)

| Approach | Preprocessing | Monthly Queries | Total Year 1 | Savings |
|----------|--------------|-----------------|--------------|---------|
| **Phase 1 Only** (Contextual Retrieval) | $0.82 | $2/month | **~$25** | - |
| **Phase 2** (Add GraphRAG) | +$9 | +$20/month | **~$274** | -91% vs original |
| **Original Plan** (GraphRAG from start) | $9 | $20/month | **$249** | Baseline |

**Result:** If Contextual Retrieval proves sufficient, **99% cheaper than original plan** ($0.82 vs $249)

---
