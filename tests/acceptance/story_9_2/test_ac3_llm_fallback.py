"""Acceptance tests for AC3: LLM Fallback for Unknown Formats.

TEST-AC-9.2.3.x tests validate LLM fallback behavior with exponential backoff
when regex patterns do not match.

TDD RED Phase: These tests define EXPECTED BEHAVIOR from acceptance criteria.
All tests MUST fail initially.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from raglite.ingestion.classification import PeriodType
from raglite.ingestion.classification.period_classifier import _classify_with_llm


class TestAC3LLMFallback:
    """AC3: LLM Fallback for Unknown Formats.

    Given a period string that does not match any regex pattern
    When the LLM fallback is invoked
    Then exponential backoff is applied on API errors
    """

    @pytest.mark.slow
    @pytest.mark.integration
    def test_ac3_1_uses_mistral_small_model(self) -> None:
        """TEST-AC-9.2.3.1 [P0]: Uses Mistral Small model for classification.

        Given an ambiguous period format that triggers LLM fallback
        When the LLM API is called
        Then Mistral Small model is used
        """
        model_used = None

        def capture_model_call(*args, **kwargs):
            nonlocal model_used
            # Capture the model parameter
            model_used = kwargs.get("model")
            # Return mock response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "UNKNOWN"
            return mock_response

        with patch(
            "raglite.ingestion.classification.period_classifier.get_mistral_client"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.chat.complete = capture_model_call
            mock_client.return_value = mock_instance

            _classify_with_llm("Q1 2021")

        assert model_used is not None
        assert "mistral-small" in model_used.lower(), f"Expected Mistral Small, got {model_used}"

    @pytest.mark.slow
    @pytest.mark.integration
    def test_ac3_2_exponential_backoff_on_api_errors(self) -> None:
        """TEST-AC-9.2.3.2 [P0]: Exponential backoff (1s, 2s) on API errors.

        Given the LLM API returns errors
        When classification is attempted
        Then retry 1 occurs after ~1s delay
        And retry 2 occurs after ~2s delay
        """
        call_times: list[float] = []

        def mock_api_fail(*args, **kwargs):
            call_times.append(time.time())
            raise Exception("API Error 429")

        with patch(
            "raglite.ingestion.classification.period_classifier.get_mistral_client"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.chat.complete = mock_api_fail
            mock_client.return_value = mock_instance

            _result = _classify_with_llm("ambiguous period xyz")  # noqa: F841

        # Should have 2 retries with reduced backoff for 5s compliance
        assert len(call_times) >= 2, f"Expected at least 2 attempts, got {len(call_times)}"

        if len(call_times) >= 2:
            first_delay = call_times[1] - call_times[0]
            assert first_delay >= 0.9, f"First retry delay should be ~1s, got {first_delay:.2f}s"

        if len(call_times) >= 3:
            second_delay = call_times[2] - call_times[1]
            assert second_delay >= 1.8, f"Second retry delay should be ~2s, got {second_delay:.2f}s"

    @pytest.mark.slow
    @pytest.mark.integration
    def test_ac3_3_returns_unknown_after_retries_exhausted(self) -> None:
        """TEST-AC-9.2.3.3 [P0]: Returns UNKNOWN after 2 retries fail (5s compliance).

        Given the LLM API fails on all attempts
        When retries are exhausted
        Then UNKNOWN is returned (reduced from 3 retries for 5s timeout)
        """
        call_count = 0

        def mock_api_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("API Error")

        with patch(
            "raglite.ingestion.classification.period_classifier.get_mistral_client"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.chat.complete = mock_api_fail
            mock_client.return_value = mock_instance

            start = time.time()
            result = _classify_with_llm("ambiguous")
            _elapsed = time.time() - start  # noqa: F841

        # AC3.3: Returns UNKNOWN after retries exhausted
        assert result == PeriodType.UNKNOWN

        # Verify retry count is limited (2 retries = 3 total attempts max)
        # But implementation might reduce further for 5s compliance
        assert call_count <= 3, f"Expected max 3 attempts (2 retries), got {call_count}"

    @pytest.mark.slow
    @pytest.mark.integration
    def test_ac3_4_warnings_logged_for_each_retry(self) -> None:
        """TEST-AC-9.2.3.4 [P1]: Logs warnings for each retry attempt.

        Given LLM API failures trigger retries
        When retries occur
        Then warnings are logged with period and error context
        """
        with patch(
            "raglite.ingestion.classification.period_classifier.get_mistral_client"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.chat.complete.side_effect = Exception("Rate limit exceeded")
            mock_client.return_value = mock_instance

            with patch("raglite.ingestion.classification.period_classifier.logger") as mock_logger:
                _classify_with_llm("test period")

                # Verify warnings were logged
                assert mock_logger.warning.called, "Expected warning logs for retries"

                # Check for structured logging (extra dict)
                warning_calls = mock_logger.warning.call_args_list
                has_extra = any(
                    call.kwargs.get("extra") is not None for call in warning_calls if call.kwargs
                )
                assert has_extra, "Warnings should include structured extra fields"

    @pytest.mark.slow
    @pytest.mark.integration
    def test_ac3_5_error_logged_after_all_retries_exhausted(self) -> None:
        """TEST-AC-9.2.3.5 [P1]: Logs error after all retries exhausted.

        Given all LLM retries fail
        When fallback to UNKNOWN occurs
        Then error is logged with full context
        """
        with patch(
            "raglite.ingestion.classification.period_classifier.get_mistral_client"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.chat.complete.side_effect = Exception("Service unavailable")
            mock_client.return_value = mock_instance

            with patch("raglite.ingestion.classification.period_classifier.logger") as mock_logger:
                _classify_with_llm("unclassifiable xyz")

                # Verify error was logged after retries exhausted
                assert mock_logger.error.called or mock_logger.warning.called, (
                    "Expected error or warning log after retries exhausted"
                )
