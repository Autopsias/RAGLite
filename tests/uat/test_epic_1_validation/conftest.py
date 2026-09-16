"""Pytest configuration and shared fixtures for Epic 1 UAT tests."""

from .fixtures import mock_external_apis, sample_email_episode
from .test_auth_config import setup_uat_authentication

__all__ = [
    "sample_email_episode",
    "mock_external_apis",
    "setup_uat_authentication",
]
