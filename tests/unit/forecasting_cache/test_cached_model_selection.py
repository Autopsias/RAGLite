"""Tests for CachedModelSelection dataclass."""

from raglite.external_data.storage import CachedModelSelection


class TestCachedModelSelection:
    """Tests for CachedModelSelection dataclass."""

    def test_is_expired_returns_false_for_valid(
        self, cached_selection_with_regressors: CachedModelSelection
    ) -> None:
        """Non-expired selection returns is_expired=False."""
        assert not cached_selection_with_regressors.is_expired

    def test_is_expired_returns_true_for_expired(
        self, expired_cached_selection: CachedModelSelection
    ) -> None:
        """Expired selection returns is_expired=True."""
        assert expired_cached_selection.is_expired
