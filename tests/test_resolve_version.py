# tests/test_resolve_version.py
import pytest
from unittest.mock import MagicMock
import git

from rich.console import Console

from helix.commands.install import DependencyDownloader

# Importe a função que está sendo testada
def resolve_version_from_spec(name, specifier, repo):
    
    downloader = DependencyDownloader(Console())
    return downloader._resolve_version_from_spec(name, specifier, repo) 


@pytest.fixture
def mock_repo():
    """Repo Git mockado com tags que devolvem strings reais"""
    repo = MagicMock(spec=git.Repo)

    # Lista de tags com nomes reais (strings), não MagicMock
    tag_data = [
        ("v2.5.0", "abc123000000"),
        ("2.4.1", "def456000000"),
        ("v2.3.9", "ghi789000000"),
        ("1.9.8", "jkl012000000"),
        ("v1.8.2", "mno345000000"),
        ("v1.8.0", "pqr678000000"),
        ("2.0.0-alpha.3", "stu901000000"),
        ("v3.0.0-rc.1", "vwx234000000"),
        ("v2.5.0+build.123", "yzab456000000"),   # ← com build metadata
        ("latest", "111111111111"),
        ("stable", "222222222222"),
        ("dev", "333333333333"),
        ("v1.0", "444444444444"),                # inválido (sem patch)
        ("final", "555555555555"),
    ]

    # Cria objetos Tag mockados que se comportam como git.Tag
    tags = []
    for tag_name, commit_sha in tag_data:
        tag = MagicMock()
        tag.name = tag_name                # ← string real
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
        ("^1.8.0", "1.9.8"),              # ← agora pega a maior 1.x.x

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
    result = resolve_version_from_spec("test-lib", specifier, mock_repo)
    assert result == expected


@pytest.mark.parametrize("specifier", [
    "branch=main",
    "tag=v2.5.0",
    "commit=abc1230",
    "commit=abc1230000000000",
])
def test_direct_prefix_returns_value_immediately(mock_repo, specifier):
    prefix, value = specifier.split("=", 1)
    expected = value if prefix != "commit" else value[:7]
    result = resolve_version_from_spec("lib", specifier, mock_repo)
    assert result == expected


def test_invalid_tags_are_ignored(mock_repo):
    """Garante que tags como 'latest', 'v1.0', 'final' são ignoradas silenciosamente"""
    # Forçamos uma spec que só aceita versões muito altas → deve ir pro HEAD
    result = resolve_version_from_spec("bad-repo", "^10.0.0", mock_repo)
    assert result == "HEAD"


def test_version_with_build_metadata_is_accepted(mock_repo):
    assert resolve_version_from_spec("lib", "==2.5.0", mock_repo) == "v2.5.0+build.123"
    assert resolve_version_from_spec("lib", "^2.5.0", mock_repo) == "v2.5.0+build.123"    