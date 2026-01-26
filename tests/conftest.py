"""Pytest configuration and shared fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_output(fixtures_dir: Path) -> str:
    """Load sample payload output."""
    return (fixtures_dir / "sample_output.txt").read_text()


@pytest.fixture
def sample_inventory(tmp_path: Path) -> Path:
    """Create a temporary inventory file."""
    inventory = tmp_path / "hosts"
    inventory.write_text("""[test]
localhost ansible_connection=local
""")
    return inventory
