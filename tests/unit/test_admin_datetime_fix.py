"""Test datetime timezone handling in admin tools.

This test verifies the fix for the issue where naive datetimes from the database
caused "can't subtract offset-naive and offset-aware datetimes" errors.
"""

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from raglite.mcp.tools.admin import _check_checkpoint_freshness


class MockModelRegistry(BaseModel):
    """Mock ModelRegistry for testing."""

    id: int | None = None
    model_type: str = "tft"
    model_version: str = "v1.0"
    checkpoint_path: str = "/tmp/test.ckpt"
    metrics_json: dict | None = None
    trained_at: datetime
    is_active: bool = True


def test_check_checkpoint_freshness_with_naive_datetime():
    """Test that naive datetime from database is handled correctly.

    This reproduces the bug where database returns naive datetime but
    code tried to subtract timezone-aware datetime.now(UTC) from it.
    """

    # Mock storage that returns naive datetime (as database does)
    class MockStorage:
        def get_active_model(self, model_type):
            # Return naive datetime as database does
            return MockModelRegistry(
                trained_at=datetime(2024, 1, 1, 12, 0, 0),  # Naive datetime
                checkpoint_path="/test.ckpt",
            )

    storage = MockStorage()
    model_list = ["tft"]
    force = False
    start_time = 0.0

    # This should NOT raise TypeError about naive/aware datetime mismatch
    result = _check_checkpoint_freshness(storage, model_list, force, start_time)

    # Result should be None because checkpoint is old (>30 days)
    assert result is None, "Old checkpoint should return None (proceed with training)"


def test_check_checkpoint_freshness_with_recent_checkpoint():
    """Test that recent checkpoint skips training."""

    # Mock storage with recent checkpoint
    class MockStorage:
        def get_active_model(self, model_type):
            # Recent checkpoint (yesterday)
            return MockModelRegistry(
                trained_at=datetime.now(UTC) - timedelta(days=1),
                checkpoint_path="/test.ckpt",
            )

    storage = MockStorage()
    model_list = ["tft"]
    force = False
    start_time = 0.0

    result = _check_checkpoint_freshness(storage, model_list, force, start_time)

    # Should return JSON response indicating training should be skipped
    assert result is not None, "Recent checkpoint should skip training"
    assert '"status": "skipped"' in result


def test_datetime_comparison_edge_cases():
    """Test various datetime timezone scenarios."""
    # Scenario 1: Naive datetime from database
    naive_dt = datetime(2024, 1, 1, 12, 0, 0)
    assert naive_dt.tzinfo is None, "Test datetime should be naive"

    # Fix: Make it timezone-aware
    aware_dt = naive_dt
    if aware_dt.tzinfo is None:
        aware_dt = aware_dt.replace(tzinfo=UTC)

    # Now comparison works
    age = datetime.now(UTC) - aware_dt
    assert age.days > 0, "Age should be positive for old datetime"

    # Scenario 2: Already timezone-aware
    aware_dt2 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    if aware_dt2.tzinfo is None:
        aware_dt2 = aware_dt2.replace(tzinfo=UTC)

    age2 = datetime.now(UTC) - aware_dt2
    assert age2.days > 0, "Age should be positive"
