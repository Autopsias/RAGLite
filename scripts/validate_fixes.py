#!/usr/bin/env python3
"""Validation script for port configuration and type annotation fixes.

This script validates that:
1. Port Configuration Fix: Tests use port 6335 (test) not 6333 (production)
2. Type Annotation Fix: No import errors when types are mocked
"""

import os
import sys

# Set test environment BEFORE importing raglite
os.environ["APP_ENV"] = "test"
os.environ["TESTING"] = "true"


def test_port_configuration():
    """Verify test environment uses correct ports."""
    from raglite.shared.config import Settings

    settings = Settings()

    print("\n=== Port Configuration Validation ===")
    print(f"APP_ENV: {settings.app_env}")
    print(f"Qdrant Port: {settings.qdrant_port} (expected: 6335)")
    print(f"PostgreSQL Port: {settings.postgres_port} (expected: 5433)")
    print(f"Collection Name: {settings.qdrant_collection_name} (expected: financial_docs_test)")
    print(f"PostgreSQL DB: {settings.postgres_db} (expected: raglite_test)")

    assert settings.qdrant_port == 6335, f"Wrong Qdrant port: {settings.qdrant_port}"
    assert settings.postgres_port == 5433, f"Wrong PostgreSQL port: {settings.postgres_port}"
    assert (
        settings.qdrant_collection_name == "financial_docs_test"
    ), f"Wrong collection: {settings.qdrant_collection_name}"
    assert settings.postgres_db == "raglite_test", f"Wrong DB: {settings.postgres_db}"

    print("✅ Port configuration correct!")
    return True


def test_type_annotations():
    """Verify type annotations don't cause import errors."""
    print("\n=== Type Annotation Validation ===")

    try:
        from raglite.shared.clients import (
            _embedding_model,
            _mistral_client,
            _postgresql_connection,
            _qdrant_client,
        )

        print("✅ All type annotations import successfully!")
        print(f"   _qdrant_client type: {type(_qdrant_client)}")
        print(f"   _embedding_model type: {type(_embedding_model)}")
        print(f"   _postgresql_connection type: {type(_postgresql_connection)}")
        print(f"   _mistral_client type: {type(_mistral_client)}")
        return True
    except Exception as e:
        print(f"❌ Type annotation error: {e}")
        return False


def main():
    """Run all validations."""
    print("=" * 60)
    print("Validating Test Orchestration Fixes")
    print("=" * 60)

    results = []

    # Test 1: Port Configuration
    try:
        results.append(("Port Configuration", test_port_configuration()))
    except Exception as e:
        print(f"❌ Port configuration test failed: {e}")
        results.append(("Port Configuration", False))

    # Test 2: Type Annotations
    try:
        results.append(("Type Annotations", test_type_annotations()))
    except Exception as e:
        print(f"❌ Type annotation test failed: {e}")
        results.append(("Type Annotations", False))

    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n🎉 All validations passed!")
        sys.exit(0)
    else:
        print("\n❌ Some validations failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
