import pytest

from knitpkg.core.version_handling import validate_version_specifier, validate_version

# --- Unit tests ---

@pytest.mark.parametrize("ref", [
    # Exact versions
    ("1.2.3", "1.2.3"),
    ("1.0.0", "1.0.0"),
    ("2.0.0", "2.0.0"),
    ("1.2.3-beta.1", "1.2.3-beta.1"),
    ("0.0.1", "0.0.1"),
    # Exact version not found
    ("9.9.9", None),
    ("1.2.3-alpha", None), # Not in available_versions

    # Caret ranges (NPM-compliant semantics)
    ("^1.2.0", "1.5.0"), # >=1.2.0 <2.0.0
    ("^1.0.0", "1.5.0"), # >=1.0.0 <2.0.0
    ("^0.1.0", "0.1.0"), # >=0.1.0 <0.2.0 (NPM: major=0, minor is breaking)
    ("^0.0.1", "0.0.1"), # >=0.0.1 <0.0.2 (NPM: major=0, minor=0, patch is breaking)
    ("^2.0.0", "2.1.0"), # >=2.0.0 <3.0.0
    ("^1.2.3-beta.1", "1.5.0"), # >=1.2.3-beta.1 <2.0.0

    # Tilde ranges (NPM-compliant semantics)
    ("~1.2.0", "1.2.3"), # >=1.2.0 <1.3.0
    ("~1.0.0", "1.0.0"), # >=1.0.0 <1.1.0
    ("~0.1.0", "0.1.0"), # >=0.1.0 <0.2.0
    ("~0.0.1", "0.0.1"), # >=0.0.1 <0.1.0
    ("~1.2.3-beta.1", "1.2.3"), # >=1.2.3-beta.1 <1.3.0

    # Complex ranges
    (">=1.0.0 <2.0.0", "1.5.0"),
    (">=1.2.0 <=1.5.0", "1.5.0"),
    (">=1.2.3-beta.1 <1.3.0", "1.2.3"),
    (">1.0.0", "2.1.0"), # Should pick highest above 1.0.0
    ("<=1.2.0", "1.2.0"), # Should pick highest below or equal to 1.2.0
    ("=1.2.3", "1.2.3"),
    ("> 1.0.0", "2.1.0"), # With space
    (">=2.0.0 <2.1.0", "2.0.5"),
    (">=3.0.0", None), # No version >=3.0.0

    # Wildcard ranges
    ("x", "2.1.0"), # Any version
    ("*", "2.1.0"), # Any version
    ("1.x", "1.5.0"), # >=1.0.0 <2.0.0
    ("1.*", "1.5.0"),
    ("1.2.x", "1.2.3"), # >=1.2.0 <1.3.0
    ("1.2.*", "1.2.3"),
    ("0.x", "0.5.0"), # >=0.0.0 <1.0.0
    ("0.0.x", "0.0.1"), # >=0.0.0 <0.1.0
    ("1.x.0", "1.5.0"), # Specific wildcard pattern, matches 1.0.0
    ("1.x.2", None), # Corrected expectation: No match in available_versions for 1.ANY.2
    ("x.1.0", "2.1.0"), # Matches any major, minor 1, patch 0. Highest is 2.1.0.
    ("x.1.x", "2.1.0"), # Matches any major, minor 1, any patch. Highest is 2.1.0.
])
def test_is_valid_ref_valid_cases(ref):
    assert validate_version_specifier(ref[0]) is True, f"'{ref}' should be valid"

@pytest.mark.parametrize("ref", [
    # Invalid formats (should return False)
    "",
    " ",
    "1.0", # Incomplete SemVer
    "1",   # Incomplete SemVer
    "1.0.0.0", # Too many parts
    "abc",
    "1.0.0-", # Incomplete pre-release
    "1.0.0+", # Incomplete build metadata
    "v1.2.3",       # Leading 'v' is not allowed
    "V1.2.3",       # Leading 'V' is not allowed
    "v1.2.3-beta.1" # Leading 'v' is not allowed
    "~v1.2.0",      # Leading 'v' is not allowed
    "^v1.2.0",      # Leading 'v' is not allowed
    "v0.0.1",       # Leading 'v' is not allowed
    "v9.9.9",       # Leading 'v' is not allowed
    "v1.0", # Incomplete SemVer with 'v'
    "^1.0", # Incomplete SemVer with caret
    "~1.0", # Incomplete SemVer with tilde
    "invalid-version",
    "latest", # Tag, not SemVer
    "1.0.0 - 2.0.0", # Not supported by range parsing logic (expects explicit operators)
    "1.0.0 <", # Incomplete range
    "> 1.0.0 <", # Incomplete range
    "1.0.0-alpha_beta", # Invalid char in pre-release
    "1.0.0+build_info", # Invalid char in build metadata
    "v1.x", # Wildcard with 'v' prefix
    "V1.2.x", # Wildcard with 'V' prefix
    "1.0.0.x", # Wildcard in invalid SemVer position
    "1.2.3.x", # Too many parts with wildcard
    "1.2.3-alpha..1", # Invalid pre-release format
    "1.2.3+build..1", # Invalid build metadata format
])
def test_is_valid_ref_invalid_cases(ref):
    """Test invalid cases."""
    assert validate_version_specifier(ref) is False, f"'{ref}' should be invalid"

# Additional tests to cover nuances of the validation regex
@pytest.mark.parametrize("ref, expected", [
    ("1.0.0-alpha", True),
    ("1.0.0+build", True), 
    ("1.0.0-alpha+build", True), 
    ("1.0.0", True), # Already covered, but to reinforce.
    (">=1.0.0", True),
    (">=1.0.0 <2.0.0", True)
])
def test_is_valid_ref_specific_regex_behavior(ref, expected):
    """Test specific behaviors of the validation regex and the function's logic."""
    assert validate_version_specifier(ref) is expected, f"'{ref}' should be {expected}"

def test_valid_version():
    assert validate_version("1.0.0")        == True
    assert validate_version("2.1.3-beta.1") == True
    assert validate_version("0.0.1")        == True

    assert validate_version("v1.0.0")       == False
    assert validate_version("1.0")          == False
    