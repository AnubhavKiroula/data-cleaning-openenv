"""Shared pytest fixtures and import-path setup for the research test suite."""

import os
import sys

import pytest

# Tests import `data.*`, `backend.*` and `envs.*` as top-level packages, so the
# repository root must be importable regardless of where pytest is invoked.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


@pytest.fixture(scope="session")
def loader():
    """A session-scoped dataset loader. Parsing the CSV once keeps tests fast."""
    from data.iot_data_loader import UCIAirQualityLoader

    return UCIAirQualityLoader()
