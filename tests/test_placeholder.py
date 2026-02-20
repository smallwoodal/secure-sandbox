"""Placeholder test so pytest has something to run on initial setup."""


def test_repo_structure():
    """Verify the basic repo structure exists."""
    from pathlib import Path

    root = Path(__file__).parent.parent
    expected_dirs = [
        "scrapers",
        "pipelines",
        "connectors",
        "schemas",
        "data/inbox",
        "output",
        "ops",
    ]
    for d in expected_dirs:
        assert (root / d).is_dir(), f"Missing directory: {d}"
