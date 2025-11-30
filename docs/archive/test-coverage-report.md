# Test Coverage Report

**Generated:** generate-test-coverage-report.py
**Story:** 3-0-6 (Test ID Traceability System)
**Purpose:** Track test coverage by story for traceability

---

## Summary Statistics

- **Total Test Files:** 29
- **Total Tests with IDs:** 200
- **Stories with Tests:** 16

### Test Type Distribution

| Test Type | Count | Percentage |
|-----------|-------|------------|
| UNIT | 96 | 48.0% |
| INTEGRATION | 78 | 39.0% |
| E2E | 26 | 13.0% |
| PERF | 0 | 0.0% |
| **Total** | **200** | **100.0%** |

### Coverage by Epic

| Epic | Stories | Total Tests |
|------|---------|-------------|
| Epic 1 | 9 | 120 |
| Epic 2 | 7 | 80 |

---

## Detailed Coverage by Story

### Story 1.5 (5 tests)

**UNIT Tests (5):**

- `1.5-UNIT-001` - test_document_metadata_creation
- `1.5-UNIT-002` - test_document_metadata_missing_required_field
- `1.5-UNIT-003` - test_chunk_creation
- `1.5-UNIT-004` - test_chunk_default_embedding
- `1.5-UNIT-005` - test_search_result_score_validation

### Story 1.6 (5 tests)

**UNIT Tests (5):**

- `1.6-UNIT-001` - test_get_qdrant_client_success
- `1.6-UNIT-002` - test_get_qdrant_client_connection_error
- `1.6-UNIT-003` - test_get_claude_client_success
- `1.6-UNIT-004` - test_get_claude_client_missing_api_key
- `1.6-UNIT-005` - test_get_claude_client_empty_api_key

### Story 1.8 (22 tests)

**UNIT Tests (22):**

- `1.8-UNIT-001` - test_mcp_server_exists
- `1.8-UNIT-002` - test_mcp_server_tools_registered
- `1.8-UNIT-003` - test_ingest_tool_success
- `1.8-UNIT-004` - test_ingest_tool_file_not_found
- `1.8-UNIT-005` - test_ingest_tool_processing_error
- `1.8-UNIT-006` - test_ingest_tool_structured_logging
- `1.8-UNIT-007` - test_query_tool_success
- `1.8-UNIT-008` - test_query_tool_empty_query
- `1.8-UNIT-009` - test_query_tool_whitespace_only_query
- `1.8-UNIT-010` - test_query_tool_search_error
- `1.8-UNIT-011` - test_query_tool_unexpected_error
- `1.8-UNIT-012` - test_query_tool_structured_logging
- `1.8-UNIT-013` - test_exception_creation
- `1.8-UNIT-014` - test_exception_inheritance
- `1.8-UNIT-026` - test_generate_citations_basic
- `1.8-UNIT-027` - test_generate_citations_multi_source
- `1.8-UNIT-028` - test_citation_format
- `1.8-UNIT-029` - test_missing_page_number
- `1.8-UNIT-030` - test_missing_source_document
- `1.8-UNIT-031` - test_citation_appended_to_text
- `1.8-UNIT-032` - test_empty_results_list
- `1.8-UNIT-033` - test_citation_ordering

### Story 1.9 (1 tests)

**INTEGRATION Tests (1):**

- `1.9-INTEGRATION-003` - test_multiple_queries

### Story 1.10 (5 tests)

**INTEGRATION Tests (5):**

- `1.10-INTEGRATION-001` - test_financial_terminology_handling
- `1.10-INTEGRATION-002` - test_metadata_completeness_validation
- `1.10-INTEGRATION-003` - test_ground_truth_validation_subset
- `1.10-INTEGRATION-004` - test_e2e_integration_flow
- `1.10-INTEGRATION-005` - test_performance_measurement

### Story 1.11 (10 tests)

**UNIT Tests (4):**

- `1.11-UNIT-010` - test_settings_load_from_env
- `1.11-UNIT-011` - test_settings_default_values
- `1.11-UNIT-012` - test_settings_missing_api_key_optional
- `1.11-UNIT-013` - test_settings_type_validation

**INTEGRATION Tests (6):**

- `1.11-INTEGRATION-001` - test_e2e_metadata_completeness
- `1.11-INTEGRATION-002` - test_e2e_citation_integration
- `1.11-INTEGRATION-003` - test_e2e_llm_synthesis_compatibility
- `1.11-INTEGRATION-004` - test_e2e_performance_validation
- `1.11-INTEGRATION-005` - test_e2e_ground_truth_metadata
- `1.11-INTEGRATION-006` - test_e2e_standard_mcp_pattern

### Story 1.12 (31 tests)

**INTEGRATION Tests (5):**

- `1.12-INTEGRATION-002` - test_retrieval_accuracy_ground_truth
- `1.12-INTEGRATION-003` - test_performance_p50_p95_latency
- `1.12-INTEGRATION-004` - test_metadata_preservation_integration
- `1.12-INTEGRATION-005` - test_metadata_filtering_integration
- `1.12-INTEGRATION-006` - test_citation_accuracy_integration

**E2E Tests (26):**

- `1.12-E2E-002` - test_unique_question_ids
- `1.12-E2E-003` - test_ids_are_sequential
- `1.12-E2E-005` - test_question_text_non_empty
- `1.12-E2E-006` - test_expected_answer_non_empty
- `1.12-E2E-007` - test_expected_keywords_non_empty
- `1.12-E2E-008` - test_page_numbers_valid
- `1.12-E2E-009` - test_expected_section_non_empty
- `1.12-E2E-010` - test_source_document_consistent
- `1.12-E2E-011` - test_all_categories_present
- `1.12-E2E-012` - test_no_invalid_categories
- `1.12-E2E-013` - test_category_distribution
- `1.12-E2E-014` - test_category_distribution_tolerance
- `1.12-E2E-015` - test_all_difficulties_present
- `1.12-E2E-016` - test_no_invalid_difficulties
- `1.12-E2E-017` - test_difficulty_distribution_exact
- `1.12-E2E-018` - test_difficulty_percentages
- `1.12-E2E-019` - test_import_ground_truth_qa
- `1.12-E2E-020` - test_ground_truth_is_list_of_dicts
- `1.12-E2E-021` - test_module_has_docstring
- `1.12-E2E-022` - test_no_duplicate_questions
- `1.12-E2E-023` - test_expected_keywords_are_relevant
- `1.12-E2E-024` - test_page_numbers_within_reasonable_range
- `1.12-E2E-025` - test_questions_are_actually_questions
- `1.12-E2E-026` - test_random_subset_selection
- `1.12-E2E-027` - test_category_balanced_subset
- `1.12-E2E-028` - test_difficulty_balanced_subset

### Story 1.13 (40 tests)

**UNIT Tests (35):**

- `1.13-UNIT-002` - test_ingest_pdf_file_not_found
- `1.13-UNIT-003` - test_ingest_pdf_corrupted
- `1.13-UNIT-004` - test_ingest_pdf_page_numbers_extracted
- `1.13-UNIT-005` - test_ingest_pdf_no_page_metadata
- `1.13-UNIT-007` - test_ingest_pdf_logging
- `1.13-UNIT-008` - test_extract_excel_success
- `1.13-UNIT-009` - test_extract_excel_multi_sheet
- `1.13-UNIT-010` - test_extract_excel_numeric_formats
- `1.13-UNIT-011` - test_extract_excel_file_not_found
- `1.13-UNIT-012` - test_extract_excel_password_protected
- `1.13-UNIT-013` - test_extract_excel_corrupted
- `1.13-UNIT-014` - test_extract_excel_sheet_numbers
- `1.13-UNIT-015` - test_extract_excel_empty_workbook
- `1.13-UNIT-016` - test_ingest_document_pdf
- `1.13-UNIT-017` - test_ingest_document_excel
- `1.13-UNIT-018` - test_ingest_document_unsupported_format
- `1.13-UNIT-019` - test_ingest_document_file_not_found
- `1.13-UNIT-021` - test_chunk_overlap
- `1.13-UNIT-022` - test_chunk_page_numbers
- `1.13-UNIT-023` - test_chunk_short_document
- `1.13-UNIT-024` - test_chunk_empty_document
- `1.13-UNIT-025` - test_chunk_invalid_parameters
- `1.13-UNIT-027` - test_embedding_dimensions
- `1.13-UNIT-028` - test_batch_processing
- `1.13-UNIT-029` - test_empty_chunk_handling
- `1.13-UNIT-030` - test_embeddings_not_none
- `1.13-UNIT-031` - test_embedding_generation_error_handling
- `1.13-UNIT-032` - test_get_embedding_model_singleton
- `1.13-UNIT-033` - test_generate_embeddings_logging
- `1.13-UNIT-035` - test_create_collection_idempotent
- `1.13-UNIT-037` - test_batch_upload_processing
- `1.13-UNIT-038` - test_metadata_preservation
- `1.13-UNIT-039` - test_empty_chunks_handling
- `1.13-UNIT-040` - test_storage_error_handling
- `1.13-UNIT-041` - test_get_qdrant_client_singleton

**INTEGRATION Tests (5):**

- `1.13-INTEGRATION-002` - test_pdf_ingestion_stores_correct_page_numbers
- `1.13-INTEGRATION-003` - test_page_attribution_accuracy_sample
- `1.13-INTEGRATION-006` - test_chunking_performance_validation
- `1.13-INTEGRATION-011` - test_storage_retrieval_roundtrip
- `1.13-INTEGRATION-012` - test_performance_validation_300_chunks

### Story 1.15 (1 tests)

**UNIT Tests (1):**

- `1.15-UNIT-001` - test_chunk_by_docling_items_extracts_page_numbers

### Story 2.1 (13 tests)

**UNIT Tests (1):**

- `2.1-UNIT-002` - test_pipeline_options_configuration

**INTEGRATION Tests (12):**

- `2.1-INTEGRATION-006` - test_ac4_160page_comparison
- `2.1-INTEGRATION-009` - test_latency_ceiling
- `2.1-INTEGRATION-010` - test_hybrid_fusion_quality
- `2.1-INTEGRATION-011` - test_baseline_thresholds_defined
- `2.1-INTEGRATION-012` - test_ground_truth_available
- `2.1-INTEGRATION-017` - test_ac2_parallel_ingestion_4_threads
- `2.1-INTEGRATION-018` - test_ac2_parallel_ingestion_8_threads
- `2.1-INTEGRATION-019` - test_ac4_thread_safety_determinism
- `2.1-INTEGRATION-020` - test_ingest_pdf_with_pypdfium_backend
- `2.1-INTEGRATION-021` - test_table_accuracy_with_pypdfium_backend
- `2.1-INTEGRATION-022` - test_table_accuracy_maintained_with_pypdfium
- `2.1-INTEGRATION-023` - test_memory_reduction_validation

### Story 2.3 (12 tests)

**INTEGRATION Tests (12):**

- `2.3-INTEGRATION-001` - test_element_metadata_stored_in_qdrant
- `2.3-INTEGRATION-002` - test_filter_chunks_by_element_type
- `2.3-INTEGRATION-003` - test_chunk_count_within_baseline_range
- `2.3-INTEGRATION-004` - test_section_context_propagated
- `2.3-INTEGRATION-005` - test_pdf_path
- `2.3-INTEGRATION-006` - test_ac4_collection_recreation_and_reingest
- `2.3-INTEGRATION-007` - test_ac4_fast_40page
- `2.3-INTEGRATION-008` - test_ac5_fast_chunk_count_validation
- `2.3-INTEGRATION-009` - test_ac5_chunk_count_validation
- `2.3-INTEGRATION-010` - test_ac6_fast_chunk_size_consistency
- `2.3-INTEGRATION-011` - test_ac6_chunk_size_consistency
- `2.3-INTEGRATION-012` - test_table_boundary_preservation

### Story 2.4 (12 tests)

**UNIT Tests (10):**

- `2.4-UNIT-001` - test_metadata_extraction_success
- `2.4-UNIT-002` - test_metadata_extraction_partial_fields
- `2.4-UNIT-003` - test_metadata_extraction_no_api_key
- `2.4-UNIT-004` - test_metadata_extraction_api_failure
- `2.4-UNIT-005` - test_metadata_caching_enabled
- `2.4-UNIT-006` - test_metadata_caching_disabled
- `2.4-UNIT-007` - test_text_truncation
- `2.4-UNIT-008` - test_extracted_metadata_all_fields
- `2.4-UNIT-009` - test_extracted_metadata_optional_fields
- `2.4-UNIT-010` - test_extracted_metadata_defaults

**INTEGRATION Tests (2):**

- `2.4-INTEGRATION-007` - test_metadata_injection_mocked
- `2.4-INTEGRATION-008` - test_metadata_filtering_mocked

### Story 2.5 (13 tests)

**INTEGRATION Tests (13):**

- `2.5-INTEGRATION-001` - test_cli_help
- `2.5-INTEGRATION-002` - test_subset_option
- `2.5-INTEGRATION-003` - test_category_filter
- `2.5-INTEGRATION-004` - test_output_file_generation
- `2.5-INTEGRATION-005` - test_verbose_output
- `2.5-INTEGRATION-006` - test_cli_help
- `2.5-INTEGRATION-007` - test_daily_check_execution
- `2.5-INTEGRATION-008` - test_tracking_log_created
- `2.5-INTEGRATION-009` - test_retrieval_accuracy_calculation
- `2.5-INTEGRATION-010` - test_attribution_accuracy_calculation
- `2.5-INTEGRATION-011` - test_performance_metrics_calculated
- `2.5-INTEGRATION-012` - test_nfr_targets_displayed
- `2.5-INTEGRATION-013` - test_exit_codes

### Story 2.11 (15 tests)

**UNIT Tests (6):**

- `2.11-UNIT-014` - test_merge_results_empty_inputs
- `2.11-UNIT-015` - test_merge_results_score_normalization_basic
- `2.11-UNIT-016` - test_merge_results_alpha_sensitivity_after_normalization
- `2.11-UNIT-017` - test_merge_results_deduplication_with_normalization
- `2.11-UNIT-018` - test_merge_results_realistic_scenario
- `2.11-UNIT-019` - test_merge_results_no_sql_degradation

**INTEGRATION Tests (9):**

- `2.11-INTEGRATION-001` - test_vector_only_query_routing
- `2.11-INTEGRATION-002` - test_sql_only_query_routing
- `2.11-INTEGRATION-003` - test_hybrid_query_routing
- `2.11-INTEGRATION-004` - test_empty_query_error
- `2.11-INTEGRATION-005` - test_result_fusion_vector_only
- `2.11-INTEGRATION-006` - test_result_fusion_sql_only
- `2.11-INTEGRATION-007` - test_result_fusion_hybrid
- `2.11-INTEGRATION-008` - test_result_fusion_deduplication
- `2.11-INTEGRATION-009` - test_result_fusion_top_k_limit

### Story 2.13 (8 tests)

**INTEGRATION Tests (8):**

- `2.13-INTEGRATION-003` - test_pg_trgm_extension_installed
- `2.13-INTEGRATION-004` - test_gin_indexes_exist
- `2.13-INTEGRATION-005` - test_similarity_function_works
- `2.13-INTEGRATION-006` - test_exact_match_fallback
- `2.13-INTEGRATION-007` - test_fuzzy_matching_thresholds
- `2.13-INTEGRATION-008` - test_case_insensitive_matching
- `2.13-INTEGRATION-009` - test_sql_only_routing
- `2.13-INTEGRATION-010` - test_vector_only_routing

### Story 2.14 (7 tests)

**UNIT Tests (7):**

- `2.14-UNIT-003` - test_multi_entity_vs_keyword
- `2.14-UNIT-008` - test_hybrid_search_fuzzy_entity_matching
- `2.14-UNIT-009` - test_hybrid_search_multi_entity_comparison
- `2.14-UNIT-010` - test_hybrid_search_keyword_detection
- `2.14-UNIT-011` - test_hybrid_search_literal_metric_matching
- `2.14-UNIT-012` - test_hybrid_search_empty_result_handling
- `2.14-UNIT-013` - test_hybrid_search_sql_generation_success

---

## Test Files

Complete list of test files with test ID counts:

| File | Test IDs | Location |
|------|----------|----------|
| `tests/e2e/test_ground_truth.py` | 26 | E2E Tests |
| `tests/integration/test_ac1_fuzzy_entity_matching.py` | 6 | Integration Tests |
| `tests/integration/test_ac4_comprehensive.py` | 1 | Integration Tests |
| `tests/integration/test_accuracy_validation.py` | 13 | Integration Tests |
| `tests/integration/test_e2e_query_validation.py` | 5 | Integration Tests |
| `tests/integration/test_element_metadata.py` | 4 | Integration Tests |
| `tests/integration/test_epic2_regression.py` | 4 | Integration Tests |
| `tests/integration/test_fixed_chunking.py` | 8 | Integration Tests |
| `tests/integration/test_ingestion_integration.py` | 5 | Integration Tests |
| `tests/integration/test_mcp_response_validation.py` | 6 | Integration Tests |
| `tests/integration/test_mcp_server.py` | 1 | Integration Tests |
| `tests/integration/test_metadata_injection.py` | 2 | Integration Tests |
| `tests/integration/test_multi_index_integration.py` | 9 | Integration Tests |
| `tests/integration/test_page_parallelism.py` | 3 | Integration Tests |
| `tests/integration/test_pypdfium_ingestion.py` | 4 | Integration Tests |
| `tests/integration/test_retrieval_integration.py` | 5 | Integration Tests |
| `tests/integration/test_sql_routing.py` | 2 | Integration Tests |
| `tests/unit/test_ac2_multi_entity_queries.py` | 1 | Unit Tests |
| `tests/unit/test_ingestion.py` | 35 | Unit Tests |
| `tests/unit/test_main.py` | 14 | Unit Tests |
| `tests/unit/test_merge_results_normalization.py` | 6 | Unit Tests |
| `tests/unit/test_metadata_extraction.py` | 10 | Unit Tests |
| `tests/unit/test_page_extraction.py` | 1 | Unit Tests |
| `tests/unit/test_pypdfium_backend.py` | 1 | Unit Tests |
| `tests/unit/test_retrieval.py` | 8 | Unit Tests |
| `tests/unit/test_shared_clients.py` | 5 | Unit Tests |
| `tests/unit/test_shared_config.py` | 4 | Unit Tests |
| `tests/unit/test_shared_models.py` | 5 | Unit Tests |
| `tests/unit/test_sql_hybrid_search.py` | 6 | Unit Tests |

---

## Usage

### Finding Tests for a Story

```bash
# Run all tests for Story 2.10
pytest tests/ -k "2.10" -v

# Run only unit tests for Story 2.10
pytest tests/unit/ -k "2.10" -v

# Run only integration tests for Epic 2
pytest tests/integration/ -k "2." -v
```

### Viewing Test IDs in Code

```bash
# Search for all Story 2.10 test IDs
grep -r "2.10-" tests/

# List all test IDs in a file
grep "@pytest.mark.test_id" tests/unit/test_query_classifier.py
```

---

## Notes

- **Test ID Format:** `{epic}.{story}-{type}-{seq}` (e.g., `2.10-UNIT-001`)
- **Parametrized Tests:** Share the same test ID across all parameter variations
- **Sequence Numbers:** Unique within each story-type combination, assigned globally across all files

**Related Documentation:**
- Testing Guidelines: `docs/testing-guidelines.md`
- Story 3-0-6: `docs/stories/3-0-6-test-id-traceability-system.md`
- Story 3-0-7: `docs/stories/3-0-7-priority-classification-system.md`
