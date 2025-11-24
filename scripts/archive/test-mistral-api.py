"""Quick test to verify Mistral API is working before full ingestion.

Tests a single metadata extraction call to check if API 502 errors are resolved.
"""

import asyncio
import sys

from mistralai import Mistral

from raglite.shared.config import settings


async def test_mistral_api():
    """Test Mistral API with a single metadata extraction call."""
    print("=" * 80)
    print("Testing Mistral API (Story 2.4 Metadata Extraction)")
    print("=" * 80)

    # Check API key
    if not settings.mistral_api_key:
        print("❌ Error: MISTRAL_API_KEY not configured in .env")
        sys.exit(1)

    print(f"API Key configured: {settings.mistral_api_key[:8]}...")
    print(f"Model: {settings.metadata_extraction_model}")
    print("\n" + "-" * 80)

    # Sample financial chunk for testing
    test_chunk = """
    Variable Costs Analysis - Portugal Cement Division
    August 2025 YTD Performance Review

    The thermal energy cost per ton increased to €23.50 in August 2025 YTD,
    representing a 12% increase compared to the same period in 2024. This increase
    is primarily attributable to higher natural gas prices in the European market.

    Total production volume: 145,000 tonnes
    Average cost per tonne: €45.20
    """

    print("Test chunk:")
    print(test_chunk.strip())
    print("\n" + "-" * 80)
    print("Sending API request...")

    try:
        # Initialize Mistral client
        client = Mistral(api_key=settings.mistral_api_key)

        from mistralai.models import SystemMessage, UserMessage

        # Use the same prompt from pipeline.py
        messages = [
            SystemMessage(
                content=(
                    "Extract metadata filters from financial document queries for RAG retrieval.\n"
                    "Return ONLY valid JSON with relevant fields. Use ONLY fields with clear evidence in query.\n"
                    "Omit fields with no evidence. Return {} if no metadata detected.\n\n"
                    "AVAILABLE FIELDS (15 total - only use when query clearly indicates):\n\n"
                    "DOCUMENT-LEVEL (7 fields):\n"
                    "- document_type: Income Statement | Balance Sheet | Cash Flow Statement | "
                    "Operational Report | Earnings Call | Management Discussion | Financial Notes\n"
                    "- reporting_period: Q1 2024 | Aug-25 | Aug-25 YTD | FY 2023 | 2024 Annual | H1 2025\n"
                    "- time_granularity: Daily | Weekly | Monthly | Quarterly | YTD | Annual | Rolling 12-Month\n"
                    "- company_name: Portugal Cement | CIMPOR | Cimpor Trading | InterCement | Secil | "
                    "Secil Group | Tunisia Cement\n"
                    "- geographic_jurisdiction: Portugal | EU | APAC | Americas | Global | Tunisia | Angola | Lebanon\n"
                    "- data_source_type: Audited | Internal Report | Regulatory Filing | Management Estimate | Preliminary\n"
                    "- version_date: 2025-08-15 | 2024-Q3-Final | 2024-12-31-Revised\n\n"
                    "SECTION-LEVEL (5 fields):\n"
                    "- section_type: Narrative | Table | Footnote | Chart Caption | Summary | List | Formula\n"
                    "- metric_category: Revenue | EBITDA | Operating Expenses | Capital Expenditure | Cash Flow | "
                    "Assets | Liabilities | Equity | Ratios | Production Volume | Cost per Unit\n"
                    "- units: EUR | USD | GBP | EUR/ton | USD/MWh | Percentage | Count | Tonnes | MWh | m³\n"
                    "- department_scope: Operations | Finance | Production | Sales | Corporate | HR | IT | Supply Chain\n\n"
                    "TABLE-SPECIFIC (3 fields - ONLY for explicit table requests):\n"
                    "- table_context: Brief keywords about table content (NOT full description)\n"
                    "- table_name: Table title keywords (e.g., 'Variable Costs', 'EBITDA Breakdown')\n"
                    "- statistical_summary: Statistical keywords (e.g., 'Mean', 'Trend', 'Variance')\n"
                )
            ),
            UserMessage(content=f"Extract metadata from this chunk:\n\n{test_chunk}"),
        ]

        response = await client.chat.complete_async(
            model=settings.metadata_extraction_model,
            messages=messages,  # type: ignore[arg-type]
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=300,
        )

        # Parse response
        if response.choices and response.choices[0].message.content:
            import json

            metadata = json.loads(response.choices[0].message.content)

            print("\n✅ SUCCESS - Mistral API is working!")
            print("\n" + "=" * 80)
            print("Extracted Metadata:")
            print("=" * 80)
            for key, value in metadata.items():
                print(f"  {key}: {value}")
            print("=" * 80)
            print(
                "\n✅ Mistral API test PASSED - Ready for full ingestion with metadata extraction!"
            )
            return True
        else:
            print("\n❌ Error: Empty response from Mistral API")
            return False

    except Exception as e:
        print(f"\n❌ FAILED - Mistral API error: {e}")
        print("\nError details:")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {str(e)}")

        if "502" in str(e) or "500" in str(e):
            print("\n⚠️  API is experiencing gateway errors (502/500)")
            print("   Recommendation: Wait 1-2 hours and retry")
        elif "429" in str(e):
            print("\n⚠️  Rate limit exceeded")
            print("   Recommendation: Wait and retry with lower concurrency")
        else:
            print("\n⚠️  Unknown API error")

        print("\n❌ Mistral API test FAILED - Do NOT proceed with full ingestion")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_mistral_api())
    sys.exit(0 if result else 1)
