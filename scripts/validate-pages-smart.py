#!/usr/bin/env python3
"""
Smart validation that distinguishes PRIMARY tables from summary references.

This script improves upon validate-pages-direct.py by:
1. Identifying section headers to find primary source tables
2. Distinguishing detailed operational tables from summaries
3. Prioritizing pages with specific section context
4. Scoring based on both keyword matches AND structural indicators

Usage:
    uv run python scripts/validate-pages-smart.py
"""

import re
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pypdf import PdfReader  # noqa: E402

from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402


def extract_page_structure(text: str) -> dict:
    """
    Analyze page structure to identify primary vs summary tables.

    Returns:
        dict with structure indicators
    """
    lines = text.split("\n")

    # Look for section headers
    section_headers = []
    for i, line in enumerate(lines):
        # Headers typically have country/region + topic + "Performance" or "Operational"
        if re.search(
            r"(Portugal|Brazil|Lebanon|Tunisia|Angola).*(?:Operational Performance|Financial Performance|Performance Review)",
            line,
            re.IGNORECASE,
        ):
            section_headers.append((i, line.strip()))

    # Look for table indicators
    has_ytd_budget_ly = bool(re.search(r"YTD.*Budget.*LY|Aug-25.*B.*Aug-24", text, re.IGNORECASE))
    has_detailed_costs = bool(
        re.search(r"Variable Costs.*EUR/ton|Fixed Costs.*EUR/ton", text, re.IGNORECASE)
    )
    has_eur_1000 = bool(re.search(r"\(1000 EUR\)|Currency.*EUR", text, re.IGNORECASE))

    # Check for summary indicators (these suggest it's NOT a primary table)
    is_summary_page = bool(
        re.search(r"Executive Summary|Overview|Contents|Index", text, re.IGNORECASE)
    )
    has_multiple_regions = (
        len(re.findall(r"Portugal|Brazil|Lebanon|Tunisia|Angola", text, re.IGNORECASE)) > 3
    )

    return {
        "section_headers": section_headers,
        "has_ytd_budget_ly": has_ytd_budget_ly,
        "has_detailed_costs": has_detailed_costs,
        "has_eur_1000": has_eur_1000,
        "is_summary_page": is_summary_page,
        "has_multiple_regions": has_multiple_regions,
        "num_section_headers": len(section_headers),
    }


def score_page_for_question(qa: dict, page_num: int, page_text: str) -> tuple[int, dict]:
    """
    Score a page's likelihood of being the PRIMARY source for a question.

    Returns:
        (score, details dict)
    """
    keywords = qa["expected_keywords"]
    expected_section = qa.get("expected_section", "")
    category = qa["category"]

    text_lower = page_text.lower()
    score = 0
    details = {}

    # 1. Keyword matches (baseline)
    keyword_matches = 0
    for keyword in keywords:
        if re.search(r"\b" + re.escape(keyword.lower()) + r"\b", text_lower):
            keyword_matches += 1
    details["keyword_matches"] = keyword_matches
    score += keyword_matches * 10  # 10 points per keyword

    # 2. Section header match (strong indicator)
    structure = extract_page_structure(page_text)
    details["structure"] = structure

    if expected_section:
        section_match = any(
            expected_section.lower() in header.lower() for _, header in structure["section_headers"]
        )
        if section_match:
            score += 50  # Big bonus for matching section header
            details["section_match"] = True

    # 3. Table structure indicators
    if structure["has_ytd_budget_ly"]:
        score += 15  # Has detailed comparison table structure
    if structure["has_detailed_costs"]:
        score += 20  # Has detailed cost breakdown
    if structure["has_eur_1000"]:
        score += 10  # Has currency specification

    # 4. Primary table indicators
    if structure["num_section_headers"] == 1:
        score += 20  # Single focused section (likely primary)
    elif structure["num_section_headers"] > 1:
        score += 5  # Multiple sections (might be primary)

    # 5. Penalties for summary pages
    if structure["is_summary_page"]:
        score -= 30  # Likely a summary, not primary source
    if structure["has_multiple_regions"]:
        score -= 20  # Cross-regional summary, not specific operational table

    # 6. Category-specific scoring
    if category == "cost_analysis" and "operational costs" in text_lower:
        score += 15
    if category == "margins" and ("ebitda" in text_lower or "margin" in text_lower):
        score += 10
    if category == "financial_performance" and "cash flow" in text_lower:
        score += 10

    details["total_score"] = score
    return score, details


def validate_question_smart(qa: dict, pages_text: dict) -> dict:
    """
    Smart validation using structure analysis.

    Args:
        qa: Ground truth question dict
        pages_text: Dict of page_number -> text

    Returns:
        dict with validation results including scores
    """
    question_id = qa["id"]
    question_text = qa["question"]
    expected_page = qa["expected_page_number"]
    category = qa["category"]

    # Score all pages
    page_scores = []
    for page_num, text in pages_text.items():
        score, details = score_page_for_question(qa, page_num, text)
        if score > 0:  # Only keep pages with positive scores
            page_scores.append((page_num, score, details))

    # Sort by score (descending)
    page_scores.sort(key=lambda x: x[1], reverse=True)

    # Determine actual page (highest score)
    if page_scores:
        actual_page, best_score, best_details = page_scores[0]
        confidence = best_score / max(1, sum(s for _, s, _ in page_scores[:3]))  # Relative to top 3
    else:
        actual_page = None
        best_score = 0
        best_details = {}
        confidence = 0.0

    # Check if expected page is in top candidates
    expected_page_rank = None
    expected_page_score = None
    for i, (page_num, score, _) in enumerate(page_scores):
        if page_num == expected_page:
            expected_page_rank = i + 1
            expected_page_score = score
            break

    # Determine status
    if actual_page == expected_page:
        status = "correct"
    elif expected_page_rank and expected_page_rank <= 3:
        status = "close"  # Expected page in top 3
    elif actual_page:
        status = "incorrect"
    else:
        status = "missing"

    return {
        "question_id": question_id,
        "question": question_text,
        "category": category,
        "expected_page": expected_page,
        "expected_page_rank": expected_page_rank,
        "expected_page_score": expected_page_score,
        "actual_page": actual_page,
        "actual_page_score": best_score,
        "best_details": best_details,
        "top_candidates": page_scores[:5],
        "confidence": confidence,
        "needs_correction": status == "incorrect",
        "status": status,
        "keywords": qa["expected_keywords"],
    }


def main():
    """Main smart validation workflow."""
    print("=" * 80)
    print("SMART GROUND TRUTH PAGE VALIDATION - Story 2.9 v2")
    print("=" * 80)
    print()
    print("Using structure-aware validation to identify PRIMARY tables...")
    print(f"Validating {len(GROUND_TRUTH_QA)} ground truth questions...")
    print()

    # Load full PDF
    full_pdf = project_root / "docs" / "sample pdf" / "2025-08 Performance Review CONSO_v2.pdf"

    print(f"📖 Loading full PDF: {full_pdf.name}")
    reader = PdfReader(full_pdf)

    pages_text = {}
    for i, page in enumerate(reader.pages):
        pages_text[i + 1] = page.extract_text()

    print(f"✅ Loaded {len(pages_text)} pages")
    print()

    # Group questions by category
    by_category = {}
    for qa in GROUND_TRUTH_QA:
        category = qa["category"]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(qa)

    # Validation results
    all_results = []

    # Validate each category
    for category, questions in sorted(by_category.items()):
        print(f"\n📋 Category: {category.upper()} ({len(questions)} questions)")
        print("-" * 80)

        for qa in questions:
            result = validate_question_smart(qa, pages_text)
            all_results.append(result)

            # Print result
            q_id = result["question_id"]
            expected = result["expected_page"]
            actual = result["actual_page"]
            status = result["status"]
            score = result["actual_page_score"]
            exp_rank = result["expected_page_rank"]

            if status == "correct":
                print(f"  ✅ Q{q_id:2d}: Page {expected} CORRECT (score: {score})")
            elif status == "close":
                print(
                    f"  🟡 Q{q_id:2d}: Page {expected} CLOSE (rank: {exp_rank}, best: {actual} score: {score})"
                )
            elif status == "incorrect":
                exp_info = f"rank: {exp_rank}" if exp_rank else "not in top"
                print(f"  ❌ Q{q_id:2d}: Page {expected} ({exp_info}) → {actual} (score: {score})")
            else:
                print(f"  ⚠️  Q{q_id:2d}: Page {expected} UNCERTAIN")

    # Summary statistics
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print()

    total = len(all_results)
    correct = sum(1 for r in all_results if r["status"] == "correct")
    close = sum(1 for r in all_results if r["status"] == "close")
    incorrect = sum(1 for r in all_results if r["status"] == "incorrect")
    missing = sum(1 for r in all_results if r["status"] == "missing")

    print(f"Total questions: {total}")
    print(f"Correct page references: {correct} ({correct / total * 100:.1f}%)")
    print(f"Close (expected in top 3): {close} ({close / total * 100:.1f}%)")
    print(f"Incorrect page references: {incorrect} ({incorrect / total * 100:.1f}%)")
    print(f"Uncertain/missing: {missing} ({missing / total * 100:.1f}%)")
    print()

    # Compare with previous validation
    print("📊 COMPARISON WITH PREVIOUS VALIDATION:")
    print("  Previous method: 9 correct (18%), 28 incorrect (56%)")
    print(
        f"  Smart method:    {correct} correct ({correct / total * 100:.1f}%), {incorrect} incorrect ({incorrect / total * 100:.1f}%)"
    )
    print()

    # Corrections needed
    corrections = [r for r in all_results if r["needs_correction"]]

    if corrections:
        print(f"\n📝 CORRECTIONS NEEDED: {len(corrections)} questions")
        print("-" * 80)

        for corr in corrections[:10]:  # Show first 10
            print(
                f"  Q{corr['question_id']:2d}: Page {corr['expected_page']} → {corr['actual_page']} (score: {corr['actual_page_score']})"
            )
            print(
                f"      Reason: {corr['best_details'].get('keyword_matches', 0)} keywords, "
                f"section_match: {corr['best_details'].get('section_match', False)}"
            )

        if len(corrections) > 10:
            print(f"  ... and {len(corrections) - 10} more")
    else:
        print("\n✅ All page references are correct!")

    # Save detailed results
    output_path = project_root / "docs" / "validation" / "story-2.9-smart-validation.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write("# Story 2.9: Smart Ground Truth Page Validation Results\n\n")
        f.write("**Validation Date:** 2025-10-25\n")
        f.write("**Validation Method:** Structure-aware smart validation\n")
        f.write(f"**Total Questions:** {total}\n\n")

        f.write("## Summary Statistics\n\n")
        f.write(f"- **Correct:** {correct} ({correct / total * 100:.1f}%)\n")
        f.write(f"- **Close (top 3):** {close} ({close / total * 100:.1f}%)\n")
        f.write(f"- **Incorrect:** {incorrect} ({incorrect / total * 100:.1f}%)\n")
        f.write(f"- **Uncertain:** {missing} ({missing / total * 100:.1f}%)\n\n")

        f.write("## Detailed Results\n\n")

        for result in all_results:
            f.write(f"### Q{result['question_id']}: {result['question'][:60]}...\n\n")
            f.write(f"- **Status:** {result['status']}\n")
            f.write(f"- **Expected Page:** {result['expected_page']}")
            if result["expected_page_rank"]:
                f.write(
                    f" (rank: {result['expected_page_rank']}, score: {result['expected_page_score']})"
                )
            f.write("\n")
            f.write(
                f"- **Actual Page:** {result['actual_page']} (score: {result['actual_page_score']})\n"
            )
            f.write(f"- **Confidence:** {result['confidence']:.0%}\n")

            if result["top_candidates"]:
                f.write("\n**Top Candidates:**\n")
                for page, score, details in result["top_candidates"][:3]:
                    f.write(f"  - Page {page}: score {score} ")
                    f.write(f"({details['keyword_matches']} keywords")
                    if details.get("section_match"):
                        f.write(", section match")
                    f.write(")\n")

            f.write("\n")

    print(f"\n📄 Detailed results saved: {output_path}")
    print()

    return all_results


if __name__ == "__main__":
    main()
