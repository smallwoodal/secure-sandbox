"""Verify repo structure exists."""

from pathlib import Path


def test_repo_structure():
    root = Path(__file__).parent.parent
    expected_dirs = ["src", "data/inbox", "output", "ops", "tests"]
    for d in expected_dirs:
        assert (root / d).is_dir(), f"Missing directory: {d}"
