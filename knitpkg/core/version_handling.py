import semver
import re

# Regex for validating a pure SemVer (major.minor.patch)
# Optionally includes pre-release and build metadata.
_SEMVER_CORE_PATTERN = r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"

# Components for the wildcard part, to prevent matching incomplete SemVer
_WILDCARD_PART = r"(?:x|X|\*)"
_NUMERIC_PART = r"(?:0|[1-9]\d*)"

# Regex for validating a "requested" string for resolve_semver_version
_VERSPEC_PATTERN = (
    r"^\s*"  # Allows leading spaces
    r"(?:"
    # 1. Exact version (e.g., "1.2.3", "v1.2.3", "1.2.3-alpha.1+build.123")
    r"(?:v|V)?" + _SEMVER_CORE_PATTERN +
    r"|"
    # 2. Caret range (e.g., "^1.2.3", "^0.0.0")
    r"\^(?:v|V)?" + _SEMVER_CORE_PATTERN +
    r"|"
    # 3. Tilde range (e.g., "~1.2.3", "~0.0.0")
    r"~" + r"(?:v|V)?" + _SEMVER_CORE_PATTERN +
    r"|"
    # 4. Wildcard versions (e.g., "1.x", "1.2.x", "1.*", "1.2.*", "*", "x")
    r"(?:"
        r"" + _NUMERIC_PART + r"\." + _NUMERIC_PART + r"\." + _WILDCARD_PART + r"|" # 1.2.x
        r"" + _NUMERIC_PART + r"\." + _WILDCARD_PART + r"\." + _WILDCARD_PART + r"|" # 1.x.x
        r"" + _NUMERIC_PART + r"\." + _WILDCARD_PART + r"|" # 1.x (implies 1.x.x)
        r"" + _WILDCARD_PART + r"\." + _WILDCARD_PART + r"\." + _WILDCARD_PART + r"|" # x.x.x
        r"" + _WILDCARD_PART + r"|" # x
        r"" + _NUMERIC_PART + r"\." + _WILDCARD_PART + r"\." + _NUMERIC_PART + r"|" # 1.x.2
        r"" + _WILDCARD_PART + r"\." + _NUMERIC_PART + r"\." + _NUMERIC_PART + r"|" # x.1.2
        r"" + _WILDCARD_PART + r"\." + _NUMERIC_PART + r"\." + _WILDCARD_PART + r"" # x.1.x
    r")" +
    r"|"
    # 5. Range operators (e.g., ">=1.0.0", "<2.0.0", ">=1.0.0 <2.0.0")
    r"(?:"
        r"(?:[<>=~^]+)\s*(?:v|V)?" + _SEMVER_CORE_PATTERN +
        r"(?:\s+(?:[<>=~^]+)\s*(?:v|V)?" + _SEMVER_CORE_PATTERN + r")*"
    r")"
    r")"
    r"\s*$"  # Allows trailing spaces
)
_VERSPEC_RE = re.compile(_VERSPEC_PATTERN)


def validate_version_specifier(verspec: str) -> bool:
    """
    Validates if the requested version string conforms to expected patterns.

    Args:
        requested (str): The version specification string to validate.

    Returns:
        bool: True if the string is a valid version specifier, False otherwise.
    """
    return bool(_VERSPEC_RE.fullmatch(verspec))


def validate_version(version: str) -> bool:
    """
    Validates if the given version string is a valid SemVer version.

    Args:
        version (str): The version string to validate.
    """
    try:
        semver.Version.parse(version)
        return True
    except ValueError:
        return False