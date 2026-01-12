# tests/test_include_parser.py

import pytest
import re

# ----------------------------------------------------------------------
# KnitPkg directive parser – uses the new @knitpkg:<directive> syntax
# ----------------------------------------------------------------------

# Pattern definition (copied from commands/install.py for testing)
KNITPKG_PATTERN = re.compile(
    r'^\s*#\s*include\s+"(?P<include>[^"]+)"'
    r'(?:\s*/\*\s*@knitpkg:(?P<directive1>\w+(?:-\w+)*)\s+"(?P<path1>[^"]+)"\s*\*/)?\s*$'
    r'|'
    r'^\s*/\*\s*@knitpkg:(?P<directive2>\w+(?:-\w+)*)\s+"(?P<path2>[^"]+)"\s*\*/\s*$',
    re.MULTILINE
)

def parse_knitpkg_line(line: str):
    """
    Parse a line containing a KnitPkg directive.

    Returns:
        dict with keys: "include", "directive", "replace"
        or None if the line does not match any supported KnitPkg pattern.
    """
    m = KNITPKG_PATTERN.match(line)
    if not m:
        return None

    include_path = m.group('include')
    directive = m.group('directive1') or m.group('directive2')
    replace_path = m.group('path1') or m.group('path2')

    # Special case: standalone /* @knitpkg:include "file.mqh" */
    if include_path is None and directive == "include":
        include_path = replace_path

    return {
        "include": include_path,
        "directive": directive,
        "replace": replace_path,
    }

# ----------------------------------------------------------------------
# Individual test cases
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "line, expected",
    [
        # 1. Simple #include – no KnitPkg directive
        (
            '#include "knitpkg/include/Calc/Calc.mqh"',
            {"include": "knitpkg/include/Calc/Calc.mqh", "directive": None, "replace": None},
        ),
        # 3. Standalone include directive
        (
            '/* @knitpkg:include "knitpkg/include/Utils.mqh" */',
            {"include": "knitpkg/include/Utils.mqh", "directive": "include", "replace": "knitpkg/include/Utils.mqh"},
        ),
        # 4. Normal include, no directive
        (
            '#include "../../autocomplete/autocomplete.mqh"',
            {"include": "../../autocomplete/autocomplete.mqh", "directive": None, "replace": None},
        ),
        # 7. Glued standalone directive
        (
            '/*@knitpkg:include "knitpkg/include/Utils.mqh"*/',
            {"include": "knitpkg/include/Utils.mqh", "directive": "include", "replace": "knitpkg/include/Utils.mqh"},
        ),
        # 9. Path with spaces inside quotes
        (
            '/* @knitpkg:include "  file with spaces.mqh  " */',
            {"include": "  file with spaces.mqh  ", "directive": "include", "replace": "  file with spaces.mqh  "},
        ),
        # 10. Invalid – missing directive name
        (
            '/* @knitpkg: "something.mqh" */',
            None,
        ),
    ],
)
def test_parse_individual_lines(line, expected):
    """Test parsing of individual lines with various formatting styles."""
    assert parse_knitpkg_line(line) == expected

# ----------------------------------------------------------------------
# Full real-world file block test
# ----------------------------------------------------------------------
def test_full_real_world_block():
    """Test against a complete real file snippet."""
    texto = '''//+------------------------------------------------------------------+
//|                                                   TestScript.mq5 |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, MetaQuotes Ltd."
#property link      "https://www.mql5.com"
#property version   "1.00"

#include "knitpkg/include/Calc/Calc.mqh"

/* @knitpkg:include "knitpkg/include/Utils.mqh" */

#include "../../autocomplete/autocomplete.mqh"

/* @knitpkg:include "knitpkg/include/Utils.mqh" */

/*@knitpkg:include "knitpkg/include/Utils.mqh"*/

/* @knitpkg: "knitpkg/include/Utils.mqh" */

/* @knitpkg:include " d " */

'''

    expected_results = [
        {"include": "knitpkg/include/Calc/Calc.mqh", "directive": None, "replace": None},
        {"include": "knitpkg/include/Utils.mqh", "directive": "include", "replace": "knitpkg/include/Utils.mqh"},
        {"include": "../../autocomplete/autocomplete.mqh", "directive": None, "replace": None},
        {"include": "knitpkg/include/Utils.mqh", "directive": "include", "replace": "knitpkg/include/Utils.mqh"},
        {"include": "knitpkg/include/Utils.mqh", "directive": "include", "replace": "knitpkg/include/Utils.mqh"},
        {"include": " d ", "directive": "include", "replace": " d "},
    ]

    results = [
        parse_knitpkg_line(line)
        for line in texto.splitlines()
        if parse_knitpkg_line(line) is not None
    ]

    assert results == expected_results
