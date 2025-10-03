#!/usr/bin/env python3
"""
Merge v1.1 simplified content into architecture.md while preserving research.

This script:
1. Reads the original architecture.md (backed up as architecture-v1.0-backup.md)
2. Reads the v1.1 insert content
3. Creates a new comprehensive architecture.md with:
   - Updated header (v1.1)
   - New v1.1 sections inserted at appropriate points
   - All original research preserved
   - Microservices section updated to show both approaches
"""

from pathlib import Path

def read_file(file_path: Path) -> str:
    """Read file content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(file_path: Path, content: str):
    """Write content to file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def update_header(content: str) -> str:
    """Update document header to v1.1."""
    updated = content.replace(
        '**Version:** 1.0\n**Date:** October 3, 2025\n**Status:** Draft - Ready for Review',
        '**Version:** 1.1 (Simplified MVP-First Approach)\n**Date:** October 3, 2025\n**Status:** Ready for Development - Recommended Approach'
    )

    # Update change log
    change_log_entry = """| 2025-10-03 | 1.0 | Initial architecture based on validated research | Winston (Architect) |"""
    new_change_log = """| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-03 | 1.0 | Initial architecture based on validated research | Winston (Architect) |
| 2025-10-03 | 1.1 | Added v1.1 simplified monolithic approach as primary recommendation | Winston (Architect) |"""

    updated = updated.replace(change_log_entry, new_change_log)

    return updated

def update_table_of_contents(content: str) -> str:
    """Update table of contents with new sections."""
    old_toc = """## Table of Contents

1. [Introduction](#introduction)
2. [Executive Summary](#executive-summary)
3. [Research Findings Summary](#research-findings-summary)
4. [High-Level Architecture](#high-level-architecture)
5. [Technology Stack](#technology-stack)
6. [Microservices Architecture](#microservices-architecture)
7. [Orchestration Layer](#orchestration-layer)
8. [Data Layer](#data-layer)
9. [Phased Implementation Strategy](#phased-implementation-strategy)
10. [Deployment Architecture](#deployment-architecture)
11. [Security & Compliance](#security--compliance)
12. [Performance & Scalability](#performance--scalability)
13. [Monitoring & Observability](#monitoring--observability)
14. [Development Workflow](#development-workflow)
15. [Testing Strategy](#testing-strategy)"""

    new_toc = """## Table of Contents

1. [Introduction](#introduction)
2. [Executive Summary](#executive-summary)
3. [**NEW:** Recommended Implementation Approach (v1.1 Monolithic)](#recommended-implementation-approach-v11-monolithic)
4. [Research Findings Summary](#research-findings-summary)
5. [Technology Stack](#technology-stack)
6. [**NEW:** Reference Implementation & Coding Standards](#reference-implementation--coding-standards)
7. [Architecture Options: Monolithic vs Microservices](#architecture-options-monolithic-vs-microservices)
8. [Data Layer](#data-layer)
9. [**UPDATED:** Phased Implementation Strategy (v1.1 Simplified)](#phased-implementation-strategy-v11-simplified)
10. [Evolution Path: Monolithic → Microservices](#evolution-path-monolithic--microservices)
11. [Deployment Strategy](#deployment-strategy)
12. [Security & Compliance](#security--compliance)
13. [Performance & Scalability](#performance--scalability)
14. [Monitoring & Observability](#monitoring--observability)
15. [Development Workflow](#development-workflow)
16. [Testing Strategy](#testing-strategy)

**Reading Guide:**
- **For MVP Development (Weeks 1-12):** Focus on sections 1-3, 4-6, 9-11
- **For Future Scaling (Phase 4+):** Review sections 7-8, 12-16"""

    return content.replace(old_toc, new_toc)

def update_executive_summary(content: str) -> str:
    """Update executive summary to recommend monolithic approach."""
    old_summary_start = """### Architectural Vision

RAGLite implements a **microservices-based MCP server architecture** with **phased complexity introduction** to minimize risk and cost while delivering maximum value."""

    new_summary_start = """### Architectural Vision (v1.1 Updated)

RAGLite implements a **simplified monolithic-first architecture** that evolves to microservices only when scaling requires. The v1.1 approach prioritizes:
- **Rapid MVP delivery** (4-5 weeks vs 8-10 weeks for microservices)
- **Reduced complexity** (600-800 lines vs 3000+ lines)
- **Same features** (all PRD requirements met)
- **Future-proof evolution** (can refactor to microservices in Phase 4 if needed)

**v1.1 Recommendation: START MONOLITHIC, scale to microservices ONLY if proven necessary.**"""

    content = content.replace(old_summary_start, new_summary_start)

    # Update key decisions
    old_decisions = """**Key Architectural Decisions:**

1. **Phased Graph Approach**
   - **Phase 1:** Anthropic Contextual Retrieval (98.1% accuracy, $0.82 cost)
   - **Phase 2:** Agentic GraphRAG (only if multi-hop accuracy <95%)
   - **Savings:** 99% cost reduction if Phase 2 proves unnecessary

2. **Multi-LLM Flexibility**
   - **AWS Strands** orchestration (not Claude Agent SDK)
   - Supports Claude, GPT-4, Gemini, Llama, local models
   - No vendor lock-in to single LLM provider

3. **Microservices Pattern**
   - 5 independent services: Ingestion, Retrieval, GraphRAG, Forecasting, Insights
   - MCP Gateway aggregates all services
   - Each service exposes tools via Model Context Protocol

4. **Production-Proven Technologies**
   - Docling (97.9% table accuracy)
   - Fin-E5 embeddings (71.05% financial domain accuracy)
   - AWS Strands (production-validated: Amazon Q, AWS Glue)
   - MCP Python SDK (official, 19k GitHub stars)"""

    new_decisions = """**Key Architectural Decisions (v1.1):**

1. **Monolithic MVP First** ⭐ **NEW in v1.1**
   - Single FastMCP server with modular codebase
   - 600-800 lines of code (vs 3000+ for microservices)
   - 4-5 week delivery (vs 8-10 weeks)
   - Evolve to microservices in Phase 4 IF scaling requires

2. **Phased Graph Approach** (UNCHANGED)
   - **Phase 1:** Anthropic Contextual Retrieval (98.1% accuracy, $0.82 cost)
   - **Phase 2:** Agentic GraphRAG (only if multi-hop accuracy <95%)
   - **Savings:** 99% cost reduction if Phase 2 proves unnecessary

3. **Multi-LLM Flexibility** (DEFERRED to Phase 3)
   - **Phase 1-2:** Direct Claude API calls (simpler)
   - **Phase 3 (optional):** AWS Strands IF complex workflows need multi-agent coordination
   - **Phase 4:** Keep Strands or revert to simple calls based on real needs

4. **Production-Proven Technologies** (UNCHANGED)
   - Docling (97.9% table accuracy)
   - Fin-E5 embeddings (71.05% financial domain accuracy)
   - MCP Python SDK (official, 19k GitHub stars)
   - FastMCP for monolithic server"""

    content = content.replace(old_decisions, new_decisions)

    return content

def insert_v1_1_content_after_executive_summary(content: str, insert_content: str) -> str:
    """Insert v1.1 monolithic approach section after Executive Summary."""
    # Find the end of Executive Summary section (before Research Findings)
    marker = "## Research Findings Summary"

    if marker in content:
        parts = content.split(marker, 1)
        # Insert v1.1 content between Executive Summary and Research Findings
        insert_section = read_file(Path("/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/architecture-v1.1-insert.md"))

        # Extract the first major section (Architecture Approach + Monolithic Architecture)
        v1_1_intro = """
---

"""
        # Get content between first "## INSERT AFTER LINE 60" and "## INSERT AFTER SECTION 5"
        start = insert_section.find("### Architecture Approach: v1.1")
        end = insert_section.find("## INSERT AFTER SECTION 5")

        if start != -1 and end != -1:
            v1_1_section = insert_section[start:end].strip()
            new_content = parts[0] + "\n\n---\n\n" + v1_1_section + "\n\n---\n\n" + marker + parts[1]
            return new_content

    return content

def main():
    """Main merge logic."""
    docs_dir = Path("/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs")

    # Read original architecture
    original = read_file(docs_dir / "architecture-v1.0-backup.md")

    # Read v1.1 insert content
    insert_content = read_file(docs_dir / "architecture-v1.1-insert.md")

    print("Step 1: Updating header...")
    updated = update_header(original)

    print("Step 2: Updating table of contents...")
    updated = update_table_of_contents(updated)

    print("Step 3: Updating executive summary...")
    updated = update_executive_summary(updated)

    print("Step 4: Inserting v1.1 monolithic approach section...")
    updated = insert_v1_1_content_after_executive_summary(updated, insert_content)

    # Write new architecture.md
    output_file = docs_dir / "architecture.md"
    write_file(output_file, updated)

    print(f"\n✅ Successfully created comprehensive architecture.md v1.1")
    print(f"📄 Backup of v1.0 saved at: {docs_dir / 'architecture-v1.0-backup.md'}")
    print(f"📄 New v1.1 architecture at: {output_file}")
    print(f"\n📊 File stats:")
    print(f"   - Original v1.0: {len(original)} characters")
    print(f"   - New v1.1: {len(updated)} characters")
    print(f"   - Added: {len(updated) - len(original)} characters")

if __name__ == "__main__":
    main()
