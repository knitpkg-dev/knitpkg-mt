# tests/test_resolve_version.py
from pathlib import Path
import pytest
from unittest.mock import MagicMock
import git

from rich.console import Console

# Import from new location
from knitpkg.core.dependency_downloader import DependencyDownloader

def resolve_version_from_spec(name, specifier, repo):
    """Helper function to test version resolution"""
    downloader = DependencyDownloader(Console(), Path.cwd())
    return downloader._resolve_version_from_spec(name, specifier, repo)

@pytest.fixture
def mock_repo():
    """Mock Git repo with real tag names (strings)"""
    repo = MagicMock(spec=git.Repo)

    tag_data = [
        ("v2.5.0", "abc123000000"),
        ("2.4.1", "def456000000"),
        ("v2.3.9", "ghi789000000"),
        ("1.9.8", "jkl012000000"),
        ("v1.8.2", "mno345000000"),
        ("v1.8.0", "pqr678000000"),
        ("2.0.0-alpha.3", "stu901000000"),
        ("v3.0.0-rc.1", "vwx234000000"),
        ("v2.5.0+build.123", "yzab456000000"),
        ("latest", "111111111111"),
        ("stable", "222222222222"),
        ("dev", "333333333333"),
        ("v1.0", "444444444444"),  # invalid (no patch)
        ("final", "555555555555"),
    ]

    tags = []
    for tag_name, commit_sha in tag_data:
        tag = MagicMock()
        tag.name = tag_name
        tag.commit.hexsha = commit_sha
        tags.append(tag)

    repo.tags = tags
    return repo

@pytest.mark.parametrize(
    "specifier, expected",
    [
        ("v2.5.0", "v2.5.0+build.123"),
        ("2.5.0", "v2.5.0+build.123"),
        ("v1.8.2", "v1.8.2"),
        ("1.8.2", "v1.8.2"),

        ("^2.0.0", "v2.5.0+build.123"),
        ("^1.8.0", "1.9.8"),

        ("~2.4.0", "2.4.1"),
        ("~1.8.0", "v1.8.2"),

        (">=2.3.0, <2.5.0", "2.4.1"),
        (">=2.4.0 <3.0.0", "v2.5.0+build.123"),
        (">1.8.0 <2.0.0", "1.9.8"),

        ("branch=main", "main"),
        ("tag=v2.5.0", "v2.5.0"),
        ("commit=abc123000000", "abc1230"),

        ("2.0.0-alpha.3", "2.0.0-alpha.3"),
        (">=2.0.0-alpha", "v3.0.0-rc.1"),

        ("^99.0.0", "HEAD"),
        ("^3.0.0", "HEAD"),
        ("100.0.0", "HEAD"),
    ]
)
def test_resolve_version_from_spec(mock_repo, specifier, expected):
    """Test version resolution with various specifiers"""
    result = resolve_version_from_spec("test-lib", specifier, mock_repo)
    assert result == expected

@pytest.mark.parametrize("specifier", [
    "branch=main",
    "tag=v2.5.0",
    "commit=abc1230",
    "commit=abc1230000000000",
])
def test_direct_prefix_returns_value_immediately(mock_repo, specifier):
    """Test that prefixed refs return immediately"""
    prefix, value = specifier.split("=", 1)
    expected = value if prefix != "commit" else value[:7]
    result = resolve_version_from_spec("lib", specifier, mock_repo)
    assert result == expected

def test_invalid_tags_are_ignored(mock_repo):
    """Ensure invalid tags like 'latest', 'v1.0', 'final' are ignored"""
    result = resolve_version_from_spec("bad-repo", "^10.0.0", mock_repo)
    assert result == "HEAD"

def test_version_with_build_metadata_is_accepted(mock_repo):
    """Test that build metadata is properly handled"""
    assert resolve_version_from_spec("lib", "==2.5.0", mock_repo) == "v2.5.0+build.123"
    assert resolve_version_from_spec("lib", "^2.5.0", mock_repo) == "v2.5.0+build.123"
