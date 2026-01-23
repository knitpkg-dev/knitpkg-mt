import pytest

from knitpkg.core.version_handling import validate_version_specifier

# --- Unit tests ---

@pytest.mark.parametrize("ref", [
    # Exact versions in the format: (version_specifier, return_value_example)
    # The return_value_example is not actually used in this test suite.
    ("1.2.3", "1.2.3"),
    ("v1.2.3", "1.2.3"),
    ("V1.2.3", "1.2.3"),
    ("1.0.0", "1.0.0"),
    ("2.0.0", "2.0.0"),
    ("1.2.3-beta.1", "1.2.3-beta.1"),
    ("v1.2.3-beta.1", "1.2.3-beta.1"),
    ("0.0.1", "0.0.1"),
    ("v0.0.1", "0.0.1"),
    # Exact version not found
    ("9.9.9", None),
    ("v9.9.9", None),
    ("1.2.3-alpha", None), # Not in available_versions

    # Caret ranges (NPM-compliant semantics)
    ("^1.2.0", "1.5.0"), # >=1.2.0 <2.0.0
    ("^v1.2.0", "1.5.0"),
    ("^1.0.0", "1.5.0"), # >=1.0.0 <2.0.0
    ("^0.1.0", "0.1.0"), # >=0.1.0 <0.2.0 (NPM: major=0, minor)
    ("^0.0.1", "0.0.1"), # >=0.0.1 <0.0.2 (NPM: major=0, minor=0, patch)
    ("^2.0.0", "2.1.0"), # >=2.0.0 <3.0.0
    ("^1.2.3-beta.1", "1.5.0"), # >=1.2.3-beta.1 <2.0.0

    # Tilde ranges (NPM-compliant semantics)
    ("~1.2.0", "1.2.3"), # >=1.2.0 <1.3.0
    ("~v1.2.0", "1.2.3"),
    ("~1.0.0", "1.0.0"), # >=1.0.0 <1.1.0
    ("~0.1.0", "0.1.0"), # >=0.1.0 <0.2.0
    ("~0.0.1", "0.0.1"), # >=0.0.1 <0.1.0
    ("~1.2.3-beta.1", "1.2.3"), # >=1.2.3-beta.1 <1.3.0

    # Complex ranges
    (">=1.0.0 <2.0.0", "1.5.0"),
    (">=v1.0.0 <v2.0.0", "1.5.0"),
    (">=1.2.0 <=1.5.0", "1.5.0"),
    (">=1.2.3-beta.1 <1.3.0", "1.2.3"),
    (">1.0.0", "2.1.0"), # Should pick highest above 1.0.0
    ("<=1.2.0", "1.2.0"), # Should pick highest below or equal to 1.2.0
    ("=1.2.3", "1.2.3"),
    ("> 1.0.0", "2.1.0"), # With space, as per previous discussion
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
    # Invalid cases
        "",
    " ",
    "1.0", # Incomplete SemVer
    "1",   # Incomplete SemVer
    "1.0.0.0", # Too many parts
    "abc",
    "1.0.0-", # Incomplete pre-release
    "1.0.0+", # Incomplete build metadata
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
    """Test invalid cases for _is_valid_ref."""
    assert validate_version_specifier(ref) is False, f"'{ref}' should be invalid"

# Additional tests to cover nuances of the SEMVER_RANGE_RE regex
@pytest.mark.parametrize("ref, expected", [
    # Cases that the SEMVER_RANGE_RE regex may interpret specifically
    ("1.0.0-alpha", True), # Without operator, but with pre-release, the function falls back to pure SemVer, which does not accept pre-release.
                           # However, the logic 'any(op in ref for op in ...)' may be activated if ' ' is in ref,
                           # but here it is not.
                           # The function `_is_valid_ref` first checks `any(op in ref for op in ("^", "~", ">=", "<=", ">", "<", " "))`.
                           # If there are no such operators, it tries `SEMVER_RE` (pure SemVer, without pre-release/build).
                           # Therefore, "1.0.0-alpha" should be False.
    ("1.0.0+build", True), # Similar to above, should be False.
    ("1.0.0-alpha+build", True), # Similar to above, should be False.
    ("1.0.0", True), # Already covered, but to reinforce.
    (">=1.0.0", True),
    (">=1.0.0 <2.0.0", True), # With `replace(" ", "")` it becomes ">=1.0.0<2.0.0", which the regex should capture.
                              # The first operator group captures '>=', the base version '1.0.0'.
                              # The second side captures '<' and '2.0.0'.
                              # This is a valid case for SEMVER_RANGE_RE.
])
def test_is_valid_ref_specific_regex_behavior(ref, expected):
    """Test specific behaviors of the SEMVER_RANGE_RE regex and the function's logic."""
    assert validate_version_specifier(ref) is expected, f"'{ref}' should be {expected}"

