"""Episode Mapper Edge Cases - Expanded Test Suite

Tests for email episode mapping functionality with focus on:
- Temporal validation (ingestion_timestamp vs reference_time)
- Timezone handling (UTC conversion, missing timezone)
- Metadata field validation (thread_id, special characters)
- Business logic correctness for email episode workflows
"""

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest


class EmailEpisode:
    """Mock Email Episode model for testing"""

    def __init__(self, **kwargs):
        self.episode_id = kwargs.get("episode_id")
        self.thread_id = kwargs.get("thread_id")
        self.reference_time = kwargs.get("reference_time")
        self.ingestion_timestamp = kwargs.get("ingestion_timestamp")
        self.episode_body = kwargs.get("episode_body", "")
        self.sender = kwargs.get("sender")
        self.recipients = kwargs.get("recipients", [])
        self.subject = kwargs.get("subject")


class EpisodeMapper:
    """Mock Episode Mapper for testing temporal validation and metadata handling"""

    def __init__(self):
        self.current_time = datetime.now(UTC)

    def map_email_to_episode(self, email_data: dict[str, Any]) -> EmailEpisode:
        """Map email data to episode with temporal validation"""

        # Extract basic fields
        sender = email_data.get("sender", "")
        recipients = email_data.get("recipients", [])
        subject = email_data.get("subject", "")

        # Handle timestamp fields with timezone validation
        reference_time = email_data.get("reference_time")
        ingestion_timestamp = email_data.get("ingestion_timestamp", self.current_time)

        # Ensure both timestamps are timezone-aware
        if reference_time and reference_time.tzinfo is None:
            raise ValueError("reference_time has no timezone")

        if ingestion_timestamp and ingestion_timestamp.tzinfo is None:
            ingestion_timestamp = ingestion_timestamp.replace(tzinfo=UTC)

        # Temporal integrity validation
        if reference_time and ingestion_timestamp:
            if ingestion_timestamp <= reference_time:
                raise ValueError("ingestion_timestamp must be after reference_time")

        # Extract thread_id with validation
        thread_id = email_data.get("thread_id")
        if not thread_id:
            thread_id = f"thread_{sender}_{subject}_{reference_time.isoformat() if reference_time else 'unknown'}"

        # Build episode body preserving special characters
        body_parts = []
        if subject:
            body_parts.append(f"Subject: {subject}")
        if sender:
            body_parts.append(f"From: {sender}")
        if recipients:
            body_parts.append(f"To: {', '.join(recipients)}")

        # Add email content preserving special characters
        content = email_data.get("content", "")
        if content:
            body_parts.append(f"Content: {content}")

        episode_body = "\n".join(body_parts)

        return EmailEpisode(
            episode_id=f"episode_{hash(str(email_data)) % 1000000}",
            thread_id=thread_id,
            reference_time=reference_time,
            ingestion_timestamp=ingestion_timestamp,
            episode_body=episode_body,
            sender=sender,
            recipients=recipients,
            subject=subject,
        )


class TestEpisodeMapperEdgeCases:
    """Test episode mapper edge cases for temporal validation and metadata handling"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mapper = EpisodeMapper()
        self.base_email_data = {
            "sender": "test@example.com",
            "recipients": ["recipient@example.com"],
            "subject": "Test Subject",
            "content": "Test email content",
        }

    def test_map_email_with_future_timestamp(self):
        """Test temporal integrity violation - ingestion_timestamp must be after reference_time"""
        # Arrange
        future_time = datetime.now(UTC) + timedelta(hours=1)
        past_time = datetime.now(UTC) - timedelta(hours=1)

        email_data = self.base_email_data.copy()
        email_data["reference_time"] = future_time
        email_data["ingestion_timestamp"] = past_time

        # Act & Assert
        with pytest.raises(ValueError, match="ingestion_timestamp must be after reference_time"):
            self.mapper.map_email_to_episode(email_data)

    def test_map_email_with_missing_timezone(self):
        """Test reference_time has no timezone (None tzinfo)"""
        # Arrange
        naive_time = datetime.now()  # No timezone

        email_data = self.base_email_data.copy()
        email_data["reference_time"] = naive_time

        # Act & Assert
        with pytest.raises(ValueError, match="reference_time has no timezone"):
            self.mapper.map_email_to_episode(email_data)

    def test_map_email_with_non_utc_timezone(self):
        """Test Expected UTC timezone but got PST"""
        # Arrange
        base_time = datetime.now(UTC)
        pst_time = (base_time - timedelta(hours=2)).astimezone(
            timezone(timedelta(hours=-8))
        )  # Convert to PST
        ingestion_time = base_time  # Current time for ingestion

        email_data = self.base_email_data.copy()
        email_data["reference_time"] = pst_time
        email_data["ingestion_timestamp"] = ingestion_time

        # Act
        episode = self.mapper.map_email_to_episode(email_data)

        # Assert - Should handle PST timezone correctly
        assert episode.reference_time.tzinfo is not None
        # PST offset varies (can be -7 or -8 depending on DST), so check it's a negative offset
        assert episode.reference_time.utcoffset().total_seconds() < 0

    def test_map_email_with_missing_optional_fields(self):
        """Test Missing required fields: thread_id"""
        # Arrange - Email without explicit thread_id
        email_data = {
            "sender": "test@example.com",
            "recipients": ["recipient@example.com"],
            "subject": "Test Subject",
            "content": "Test email content",
            # No thread_id - should be auto-generated
        }

        # Act
        episode = self.mapper.map_email_to_episode(email_data)

        # Assert
        assert episode.thread_id is not None
        assert episode.thread_id.startswith("thread_")
        assert "test@example.com" in episode.thread_id
        assert "Test Subject" in episode.thread_id

    def test_map_email_with_special_chars_in_email_addresses(self):
        """Test Special characters not appearing in episode_body"""
        # Arrange
        email_data = {
            "sender": "test+tag@example.com",
            "recipients": ["user.name+label@domain.co.uk", "another@sub.domain.org"],
            "subject": "Test with special chars: @#$%^&*()",
            "content": "Content with special email addresses and chars: test+work@company.com",
        }

        # Act
        episode = self.mapper.map_email_to_episode(email_data)

        # Assert - Special characters should be preserved in episode_body
        assert "test+tag@example.com" in episode.episode_body
        assert "user.name+label@domain.co.uk" in episode.episode_body
        assert "another@sub.domain.org" in episode.episode_body
        assert "test+work@company.com" in episode.episode_body
        assert "@#$%^&*()" in episode.episode_body

    def test_map_email_with_utc_timezone(self):
        """Test UTC timezone handling"""
        # Arrange
        base_time = datetime.now(UTC)
        utc_time = base_time - timedelta(hours=2)  # UTC time well in past
        ingestion_time = base_time  # Current time for ingestion

        email_data = self.base_email_data.copy()
        email_data["reference_time"] = utc_time
        email_data["ingestion_timestamp"] = ingestion_time

        # Act
        episode = self.mapper.map_email_to_episode(email_data)

        # Assert
        assert episode.reference_time.tzinfo is not None
        assert episode.reference_time.utcoffset().total_seconds() == 0  # UTC offset

    def test_map_email_with_empty_recipients(self):
        """Test email with empty recipients list"""
        # Arrange
        email_data = {
            "sender": "test@example.com",
            "recipients": [],
            "subject": "Test Subject",
            "content": "Test content",
        }

        # Act
        episode = self.mapper.map_email_to_episode(email_data)

        # Assert
        assert episode.recipients == []
        assert "To:" not in episode.episode_body or episode.episode_body.endswith("To: ")

    def test_map_email_with_minimal_data(self):
        """Test email mapping with minimal required data"""
        # Arrange - Only sender (minimal requirement)
        email_data = {"sender": "minimal@example.com"}

        # Act
        episode = self.mapper.map_email_to_episode(email_data)

        # Assert
        assert episode.sender == "minimal@example.com"
        assert episode.thread_id is not None
        assert episode.episode_id is not None
