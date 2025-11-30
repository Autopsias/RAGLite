# Test Priority Distribution Report

**Generated:** 2025-11-05
**Total Tests:** 379

## Summary

This report shows the distribution of test priorities across the RAGLite
test suite, enabling smart CI/CD execution strategies.

## Distribution

| Priority | Count | Percentage | Target | Status |
|----------|-------|------------|--------|--------|
| P0 | 82 | 21.6% | 15-20% | ⚠️ |
| P1 | 143 | 37.7% | 30-40% | ✅ |
| P2 | 146 | 38.5% | 30-40% | ✅ |
| P3 | 8 | 2.1% | 10-20% | ⚠️ |

## Execution Times (Estimated)

| Test Set | Priority | Tests | Est. Time |
|----------|----------|-------|-----------|
| Smoke Tests | P0 only | 82 | ~18 min |
| Pre-Merge | P0+P1 | 225 | ~49 min |
| Full Suite | All | 379 | ~82 min |

## CI Cost Optimization

**Current CI workflow:**
- Full suite every commit: ~82 min × 50 commits/day
- **Total CI time:** ~68.4 hours/day

**With priority-based CI:**
- Pre-merge (P0+P1): ~49 min × 50 commits/day
- **Total CI time:** ~40.6 hours/day
- **Savings:** 41% reduction in CI time

## Priority Definitions

| Priority | Definition | Execution |
|----------|-----------|-----------|
| **P0** | Accuracy gates, security, data corruption prevention | Every commit |
| **P1** | Core features, common user workflows | Pre-merge |
| **P2** | Edge cases, integrations, performance optimizations | Nightly |
| **P3** | Nice-to-have, rare scenarios, performance benchmarks | Weekly |

## Test Commands

```bash
# Run P0 smoke tests (critical path only)
pytest tests/ -k 'priority and P0'

# Run P0+P1 pre-merge tests
pytest tests/ -k 'priority and (P0 or P1)'

# Run full test suite
pytest tests/
```

## Detailed Test Breakdown

### P0 Tests (82 tests)

**test_ac4_comprehensive.py** (3 tests)
  - test_ac4_160page_comparison
  - test_ac4_160page_doclingparse_baseline
  - test_ac4_160page_pypdfium_optimized

**test_accuracy_validation.py** (2 tests)
  - test_nfr_targets_displayed
  - test_performance_metrics_calculated

**test_e2e_query_validation.py** (5 tests)
  - test_e2e_integration_flow
  - test_financial_terminology_handling
  - test_ground_truth_validation_subset
  - test_metadata_completeness_validation
  - test_performance_measurement

**test_element_metadata.py** (2 tests)
  - test_chunk_count_within_baseline_range
  - test_section_context_propagated

**test_epic2_regression.py** (4 tests)
  - test_attribution_accuracy_floor
  - test_baseline_thresholds_defined
  - test_ground_truth_available
  - test_retrieval_accuracy_floor

**test_fixed_chunking.py** (3 tests)
  - test_ac4_collection_recreation_and_reingest
  - test_ac4_fast_40page
  - test_table_boundary_preservation

**test_ground_truth.py** (28 tests)
  - test_all_categories_present
  - test_all_difficulties_present
  - test_all_required_fields_present
  - test_category_balanced_subset
  - test_category_distribution
  - ... (23 more tests)

**test_hybrid_search_integration.py** (4 tests)
  - test_hybrid_search_exact_numbers
  - test_hybrid_search_financial_terms
  - test_hybrid_search_full_ground_truth
  - test_hybrid_vs_semantic_comparison

**test_ingestion.py** (3 tests)
  - test_batch_processing
  - test_metadata_preservation
  - test_store_vectors_basic

**test_ingestion_integration.py** (1 tests)
  - test_page_attribution_accuracy_sample

**test_mcp_response_validation.py** (2 tests)
  - test_e2e_ground_truth_metadata
  - test_e2e_performance_validation

**test_metadata_extraction.py** (3 tests)
  - test_metadata_caching_disabled
  - test_metadata_caching_enabled
  - test_metadata_extraction_api_failure

**test_metadata_injection.py** (5 tests)
  - test_ingestion_without_openai_key
  - test_metadata_filtering
  - test_metadata_filtering_mocked
  - test_metadata_injection_into_chunks
  - test_metadata_injection_mocked

**test_page_parallelism.py** (1 tests)
  - test_ac2_parallel_ingestion_4_threads

**test_pypdfium_ingestion.py** (3 tests)
  - test_memory_reduction_validation
  - test_table_accuracy_maintained_with_pypdfium
  - test_table_accuracy_with_pypdfium_backend

**test_retrieval_integration.py** (3 tests)
  - test_citation_accuracy_integration
  - test_performance_p50_p95_latency
  - test_retrieval_accuracy_ground_truth

**test_shared_clients.py** (4 tests)
  - test_get_claude_client_empty_api_key
  - test_get_claude_client_missing_api_key
  - test_get_claude_client_success
  - test_get_qdrant_client_success

**test_shared_config.py** (3 tests)
  - test_settings_load_from_env
  - test_settings_missing_api_key_optional
  - test_settings_type_validation

**test_shared_models.py** (2 tests)
  - test_document_metadata_creation
  - test_document_metadata_missing_required_field

**test_story_2_14_excerpt_validation.py** (1 tests)
  - test_ac3_metrics_accuracy

### P1 Tests (143 tests)

**test_ac1_fuzzy_entity_matching.py** (1 tests)
  - test_similarity_function_works

**test_accuracy_validation.py** (10 tests)
  - test_category_filter
  - test_cli_help
  - test_cli_help
  - test_daily_check_execution
  - test_exit_codes
  - ... (5 more tests)

**test_element_metadata.py** (1 tests)
  - test_filter_chunks_by_element_type

**test_epic2_regression.py** (2 tests)
  - test_hybrid_fusion_quality
  - test_latency_ceiling

**test_fixed_chunking.py** (4 tests)
  - test_ac5_chunk_count_validation
  - test_ac5_fast_chunk_count_validation
  - test_ac6_chunk_size_consistency
  - test_ac6_fast_chunk_size_consistency

**test_hybrid_search.py** (12 tests)
  - test_bm25_index_creation_success
  - test_bm25_index_parameters
  - test_bm25_query_relevant_ranking
  - test_bm25_query_scores
  - test_hybrid_search_bm25_unavailable_fallback
  - ... (7 more tests)

**test_ingestion.py** (9 tests)
  - test_embedding_dimensions
  - test_embedding_generation_error_handling
  - test_embeddings_not_none
  - test_generate_embeddings_basic
  - test_generate_embeddings_logging
  - ... (4 more tests)

**test_ingestion_integration.py** (10 tests)
  - test_chunking_performance_validation
  - test_embedding_dimensions_validation_direct
  - test_embedding_generation_end_to_end
  - test_empty_document_embedding_handling
  - test_ingest_financial_pdf_with_tables
  - ... (5 more tests)

**test_main.py** (8 tests)
  - test_ingest_tool_file_not_found
  - test_ingest_tool_processing_error
  - test_ingest_tool_structured_logging
  - test_ingest_tool_success
  - test_mcp_server_exists
  - ... (3 more tests)

**test_main_integration.py** (6 tests)
  - test_mcp_ingest_then_query_flow
  - test_mcp_query_execution_real_qdrant
  - test_mcp_server_initialization
  - test_mcp_tool_discovery
  - test_query_empty_collection
  - ... (1 more tests)

**test_mcp_response_validation.py** (3 tests)
  - test_e2e_citation_integration
  - test_e2e_llm_synthesis_compatibility
  - test_e2e_metadata_completeness

**test_mcp_server.py** (2 tests)
  - test_health_check
  - test_query_tool

**test_merge_results_normalization.py** (6 tests)
  - test_merge_results_alpha_sensitivity_after_normalization
  - test_merge_results_deduplication_with_normalization
  - test_merge_results_empty_inputs
  - test_merge_results_no_sql_degradation
  - test_merge_results_realistic_scenario
  - ... (1 more tests)

**test_metadata_injection.py** (5 tests)
  - test_chunks_without_metadata_fields
  - test_cost_budget_compliance
  - test_cost_budget_compliance_mocked
  - test_cost_tracking_mocked
  - test_cost_tracking_single_document

**test_multi_index_integration.py** (8 tests)
  - test_hybrid_query_routing
  - test_result_fusion_deduplication
  - test_result_fusion_hybrid
  - test_result_fusion_sql_only
  - test_result_fusion_top_k_limit
  - ... (3 more tests)

**test_page_parallelism.py** (1 tests)
  - test_ac2_parallel_ingestion_8_threads

**test_pypdfium_ingestion.py** (1 tests)
  - test_ingest_pdf_with_pypdfium_backend

**test_query_classifier.py** (8 tests)
  - test_classification_latency
  - test_empty_query
  - test_hybrid_classification
  - test_numeric_pattern_detection
  - test_overall_accuracy
  - ... (3 more tests)

**test_response_formatting.py** (1 tests)
  - test_query_result_score_range

**test_retrieval.py** (7 tests)
  - test_citation_ordering
  - test_empty_query_handling
  - test_generate_query_embedding_empty_query
  - test_generate_query_embedding_model_failure
  - test_generate_query_embedding_success
  - ... (2 more tests)

**test_retrieval_integration.py** (1 tests)
  - test_search_integration_end_to_end

**test_shared_clients.py** (1 tests)
  - test_get_qdrant_client_connection_error

**test_shared_config.py** (1 tests)
  - test_settings_default_values

**test_shared_models.py** (3 tests)
  - test_chunk_creation
  - test_chunk_default_embedding
  - test_search_result_score_validation

**test_sql_hybrid_search.py** (7 tests)
  - test_hybrid_search_empty_result_handling
  - test_hybrid_search_fuzzy_entity_matching
  - test_hybrid_search_keyword_detection
  - test_hybrid_search_literal_metric_matching
  - test_hybrid_search_multi_entity_comparison
  - ... (2 more tests)

**test_sql_routing.py** (15 tests)
  - test_empty_results_handling
  - test_fuse_deduplicates_overlapping_results
  - test_fuse_empty_results
  - test_fuse_respects_top_k
  - test_fuse_sql_only
  - ... (10 more tests)

**test_story_2_14_excerpt_validation.py** (3 tests)
  - test_ac6_extraction_accuracy
  - test_excerpt_overall_accuracy
  - test_excerpt_query

**test_table_retrieval.py** (7 tests)
  - test_search_handles_database_unavailable
  - test_search_tables_basic
  - test_search_tables_empty_query
  - test_search_tables_metadata_completeness
  - test_search_tables_score_ordering
  - ... (2 more tests)

### P2 Tests (146 tests)

**test_ac1_fuzzy_entity_matching.py** (7 tests)
  - test_case_insensitive_matching
  - test_exact_match_fallback
  - test_fuzzy_matching_portugal_cement
  - test_fuzzy_matching_thresholds
  - test_fuzzy_matching_tunisia_cement
  - ... (2 more tests)

**test_ac2_multi_entity_queries.py** (6 tests)
  - test_comparison_keyword_detection
  - test_multi_entity_between_keyword
  - test_multi_entity_comparison_portugal_vs_tunisia
  - test_multi_entity_comparison_which_higher
  - test_multi_entity_higher_lower
  - ... (1 more tests)

**test_accuracy_validation.py** (1 tests)
  - test_attribution_accuracy_calculation

**test_element_metadata.py** (1 tests)
  - test_element_metadata_stored_in_qdrant

**test_fixed_chunking.py** (1 tests)
  - test_pdf_path

**test_hybrid_search.py** (1 tests)
  - test_bm25_index_empty_chunks

**test_ingestion.py** (22 tests)
  - test_batch_upload_processing
  - test_chunk_document_basic
  - test_chunk_empty_document
  - test_chunk_overlap
  - test_chunk_page_numbers
  - ... (17 more tests)

**test_ingestion_integration.py** (2 tests)
  - test_extract_financial_excel_multi_sheet
  - test_performance_validation_300_chunks

**test_main.py** (6 tests)
  - test_exception_creation
  - test_exception_inheritance
  - test_query_tool_empty_query
  - test_query_tool_search_error
  - test_query_tool_unexpected_error
  - ... (1 more tests)

**test_mcp_response_validation.py** (1 tests)
  - test_e2e_standard_mcp_pattern

**test_mcp_server.py** (1 tests)
  - test_multiple_queries

**test_metadata_extraction.py** (7 tests)
  - test_extracted_metadata_all_fields
  - test_extracted_metadata_defaults
  - test_extracted_metadata_optional_fields
  - test_metadata_extraction_no_api_key
  - test_metadata_extraction_partial_fields
  - ... (2 more tests)

**test_multi_index_integration.py** (1 tests)
  - test_empty_query_error

**test_page_extraction.py** (5 tests)
  - test_chunk_by_docling_items_extracts_page_numbers
  - test_chunk_by_docling_items_handles_missing_prov
  - test_chunk_by_docling_items_handles_table_items
  - test_chunk_by_docling_items_maintains_chunk_size
  - test_chunk_by_docling_items_respects_page_boundaries

**test_period_normalizer.py** (36 tests)
  - test_detect_period_aug_25
  - test_detect_period_aug_25_ytd
  - test_detect_period_august_2025
  - test_detect_period_case_insensitive
  - test_detect_period_fiscal_year
  - ... (31 more tests)

**test_pypdfium_backend.py** (4 tests)
  - test_backend_import_successful
  - test_backend_type_is_correct
  - test_document_converter_accepts_pypdfium_backend
  - test_pipeline_options_configuration

**test_response_formatting.py** (8 tests)
  - test_citation_format
  - test_edge_case_metadata
  - test_empty_results_handling
  - test_metadata_completeness_validation
  - test_query_request_validation
  - ... (3 more tests)

**test_retrieval.py** (11 tests)
  - test_citation_appended_to_text
  - test_citation_format
  - test_empty_results_list
  - test_generate_citations_basic
  - test_generate_citations_multi_source
  - ... (6 more tests)

**test_retrieval_integration.py** (2 tests)
  - test_metadata_filtering_integration
  - test_metadata_preservation_integration

**test_story_2_14_excerpt_validation.py** (2 tests)
  - test_ac1_single_entity_accuracy
  - test_ac2_comparison_accuracy

**test_table_aware_chunking.py** (7 tests)
  - test_split_large_table_by_rows_headers_preserved
  - test_split_large_table_context_prefix
  - test_split_large_table_edge_case_empty_table
  - test_split_large_table_edge_case_single_row
  - test_split_large_table_small_table
  - ... (2 more tests)

**test_table_retrieval.py** (3 tests)
  - test_search_tables_no_matches
  - test_search_tables_with_metadata_filter_basic
  - test_search_tables_with_table_content

**test_transposed_table_extraction.py** (11 tests)
  - test_detect_transposed_multi_header
  - test_detect_transposed_single_header
  - test_extract_column_name_generation
  - test_extract_handles_empty_cells
  - test_extract_metadata_fields
  - ... (6 more tests)

### P3 Tests (8 tests)

**test_ingestion.py** (7 tests)
  - test_chunk_invalid_parameters
  - test_extract_excel_corrupted
  - test_extract_excel_file_not_found
  - test_extract_excel_password_protected
  - test_ingest_pdf_corrupted
  - ... (2 more tests)

**test_retrieval.py** (1 tests)
  - test_connection_error_handling


---

**Report generated by:** `scripts/analyze-test-priorities.py`
**Story:** 3-0-7 (Priority Classification System)
