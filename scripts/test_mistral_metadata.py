"""Test script for Mistral Small 3.2 metadata extraction.

This script validates that the Mistral API integration works correctly
and can extract metadata from sample financial document chunks.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.pipeline import extract_chunk_metadata  # noqa: E402
from raglite.shared.config import settings  # noqa: E402


async def test_metadata_extraction():
    """Test metadata extraction on sample chunk."""

    # Sample financial chunk from Portugal Cement operational report
    sample_chunk = """
    Portugal Cement - Operational Performance Report
    Period: Aug-25 YTD

    Variable Costs Summary:
    - Thermal Energy: 5.8 EUR/ton
    - External Electricity: 61.4 EUR/MWh
    - Raw Materials: 3.5 EUR/ton
    - Packaging: 2.1 EUR/ton

    Department: Operations
    Business Unit: Portugal Cement
    """

    print("🧪 Testing Mistral Small 3.2 Metadata Extraction")
    print("=" * 60)
    print(f"\nAPI Key configured: {'✅ Yes' if settings.mistral_api_key else '❌ No'}")
    print(f"Model: {settings.metadata_extraction_model}")
    print("\nSample chunk:")
    print("-" * 60)
    print(sample_chunk.strip())
    print("-" * 60)

    try:
        print("\n🔄 Calling Mistral API...")
        metadata = await extract_chunk_metadata(sample_chunk, "test_chunk_001")

        print("\n✅ SUCCESS! Metadata extracted:")
        print(f"  - Fiscal Period: {metadata.fiscal_period}")
        print(f"  - Company Name: {metadata.company_name}")
        print(f"  - Department: {metadata.department_name}")

        # Validate expected values
        expected_period = "Aug-25 YTD"
        expected_company = "Portugal Cement"
        expected_dept = "Operations"

        print("\n📊 Validation:")
        period_match = expected_period.lower() in (metadata.fiscal_period or "").lower()
        company_match = expected_company.lower() in (metadata.company_name or "").lower()
        dept_match = expected_dept.lower() in (metadata.department_name or "").lower()

        print(f"  - Period contains '{expected_period}': {'✅' if period_match else '❌'}")
        print(f"  - Company contains '{expected_company}': {'✅' if company_match else '❌'}")
        print(f"  - Department contains '{expected_dept}': {'✅' if dept_match else '❌'}")

        if period_match and company_match and dept_match:
            print("\n🎉 ALL VALIDATIONS PASSED!")
            return True
        else:
            print("\n⚠️  Some validations failed - check extracted values")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"Error type: {type(e).__name__}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_metadata_extraction())
    sys.exit(0 if success else 1)
