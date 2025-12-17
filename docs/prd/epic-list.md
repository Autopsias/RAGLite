# Epic List

**Epic 1: Foundation & Accurate Retrieval**
*Goal:* Deliver a working conversational financial Q&A system with 90%+ retrieval accuracy that enables users to ask natural language questions via MCP and receive accurate, source-attributed answers from company financial documents.

**Epic 2: Advanced RAG Architecture Enhancement** 🔴 **CRITICAL** (IN PROGRESS)
*Goal:* Achieve minimum 70% retrieval accuracy through staged RAG architecture enhancement. Following element-aware chunking catastrophic failure (42% accuracy, -14pp regression), implement PDF ingestion optimization (Phase 1: 1.7-2.5x speedup) followed by research-validated fixed 512-token chunking (Phase 2A: 68-72% expected accuracy), with contingency paths to Structured Multi-Index (Phase 2B: 70-80% accuracy) or Hybrid GraphRAG Architecture (Phase 2C: 75-92% accuracy) if decision gates require escalation.

*Priority:* CRITICAL (blocks Epic 3-5) | *Status:* IN PROGRESS (Phase 1 starting) | *Timeline:* 2-3 weeks (best case, Phase 1+2A) to 18 weeks (worst case, all contingencies) | *Decision Gate:* T+17 (Week 3, Day 3 - AC3 validation: ≥70% required)

**Epic 3: AI Intelligence & Orchestration**
*Goal:* Enable multi-step reasoning and complex analytical workflows through agentic orchestration, allowing the system to autonomously execute analytical tasks requiring planning, tool use, and iterative reasoning.

**Epic 4: Forecasting & Proactive Insights**
*Goal:* Deliver predictive intelligence and strategic recommendations through AI-powered forecasting and autonomous insight generation, enabling the system to proactively surface trends, anomalies, and strategic priorities.

**Epic 6: Advanced Forecasting with External Data** ✅ **COMPLETE**
*Goal:* Enhance forecasting capabilities with multi-variate models using external Portuguese/EU data sources for cement industry demand prediction, enabling correlation analysis between macro-economic drivers and business KPIs.

*Priority:* P0 | *Status:* COMPLETE | *Completed:* 2025-12-17 | *Dependencies:* Epic 4 (DONE) | *Technology Stack:* PostgreSQL 16.10 LTS, APScheduler 3.10+, scikit-learn 1.5+, XGBoost 2.1+, LightGBM, CatBoost, Chronos-2, TFT (all operational) | *Result:* 17/20 variables passing validation (baseline established)

**Epic 7: Intelligent Model Selection Framework** 🟡 **READY FOR IMPLEMENTATION**
*Goal:* Implement intelligent per-variable model selection through cross-validation, adding ARIMA/ETS statistical models and selecting optimal model per variable based on data characteristics and holdout accuracy.

*Priority:* P0 | *Status:* READY FOR IMPLEMENTATION | *Timeline:* 10 days (2 weeks) | *Dependencies:* Epic 6 (COMPLETE) | *Technology Stack:* pmdarima (Auto-ARIMA), statsmodels (ETS, ADF/KPSS) | *Success Criteria:* 15/20 variables meeting MAPE targets (vs 6/20 current), Average FQS >75 (vs 65.9 current)

**Epic 5: Production Readiness & Real-Time Operations**
*Goal:* Deploy production-ready cloud infrastructure with real-time document updates, performance optimization, and monitoring to deliver a reliable, scalable system ready for daily use and team rollout.

---
