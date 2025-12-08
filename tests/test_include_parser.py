# tests/test_include_parser.py
import re
import pytest

# @helix.<directive> regular expression under test
from helix.commands.mkinc import _resolve_includes_pattern as pattern


def parse_helix_line(line: str):
    """
    Parse a single line using the original regex.
    Returns a dict with keys: include, directive, replace
    Returns None if the line does not match the expected Helix patterns.
    """
    m = pattern.match(line)
    if not m:
        return None

    # Extract values safely
    include_path = m.group('include')          # from normal #include
    directive    = m.group('directive1') or m.group('directive2')
    replace_path = m.group('path1') or m.group('path2')

    # Special case: standalone /* @helix.include "file.mqh" */
    # → the real included file is the one inside the comment that follows @helix.include
    if include_path is None and directive == "include":
        include_path = replace_path

    return {
        "include": include_path,   # may be None only for invalid lines (won't happen here)
        "directive": directive,    # None if no @helix directive
        "replace": replace_path,   # None if no @helix directive
    }


# ----------------------------------------------------------------------
# Parameterized unit tests – covers every realistic variation
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "line, expected",
    [
        # 1. Plain #include – no Helix directive
        (
            '#include "helix/include/Calc/Calc.mqh"',
            {"include": "helix/include/Calc/Calc.mqh", "directive": None, "replace": None},
        ),
        # 2. #include with normal spaced Helix comment
        (
            '#include "../../old.mqh" /* @helix.replacewith "helix/new.mqh" */',
            {"include": "../../old.mqh", "directive": "replacewith", "replace": "helix/new.mqh"},
        ),
        # 3. Standalone Helix include directive
        (
            '/* @helix.include "helix/include/Utils.mqh" */',
            {"include": "helix/include/Utils.mqh", "directive": "include", "replace": "helix/include/Utils.mqh"},
        ),
        # 4. Normal include without directive
        (
            '#include "../../autocomplete/autocomplete.mqh"',
            {"include": "../../autocomplete/autocomplete.mqh", "directive": None, "replace": None},
        ),
        # 5. Helix comment with no spaces around
        (
            '#include "../../old.mqh" /*@helix.replacewith "helix/include/Bar/Bar.mqh"*/',
            {"include": "../../old.mqh", "directive": "replacewith", "replace": "helix/include/Bar/Bar.mqh"},
        ),
        # 6. Fully glued extreme case (real-world minified output)
        (
            '#include"../../old.mqh"/*@helix.replacewith"helix/include/Bar/Bar.mqh"*/',
            None,  # This case is NOT supported by the original regex → expected None
        ),
        # 7. Standalone glued version
        (
            '/*@helix.include "helix/include/Utils.mqh"*/',
            {"include": "helix/include/Utils.mqh", "directive": "include", "replace": "helix/include/Utils.mqh"},
        ),
        # 8. With trailing spaces and tabs
        (
            '#include "simple.mqh"     /* @helix.replacewith "novo/caminho.mqh" */',
            {"include": "simple.mqh", "directive": "replacewith", "replace": "novo/caminho.mqh"},
        ),
        # 9. Path containing whitespace inside quotes (must be preserved)
        (
            '/* @helix.include " d " */',
            {"include": " d ", "directive": "include", "replace": " d "},
        ),
        # 10. Invalid – missing directive name
        (
            '/* @helix. "helix/include/Utils.mqh" */',
            None,
        ),
    ],
)
def test_parse_individual_lines(line, expected):
    """Test each line pattern individually."""
    assert parse_helix_line(line) == expected


# ----------------------------------------------------------------------
# Full block test – matches exactly the content you provided
# ----------------------------------------------------------------------
def test_full_real_world_block():
    """Test the complete multi-line snippet you posted – must match reality."""
    texto = '''//+------------------------------------------------------------------+
//|                                                   TestScript.mq5 |
//|                                  Copyright 2025, Douglas Rechia. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, MetaQuotes Ltd."
#property link      "https://www.mql5.com"
#property version   "1.00"

#include "helix/include/Calc/Calc.mqh"
#include "../../old.mqh" /* @helix.replacewith "helix/new.mqh" */
/* @helix.include "helix/include/Utils.mqh" */

#include "../../autocomplete/autocomplete.mqh"
#include "../../old.mqh" /* @helix.replacewith "helix/include/Bar/Bar.mqh" */
#include "../../old.mqh" /*@helix.replacewith "helix/include/Bar/Bar.mqh"*/
/* @helix.include "helix/include/Utils.mqh" */
/*@helix.include "helix/include/Utils.mqh"*/
#include "simple.mqh"     /* @helix.replacewith "novo/caminho.mqh" */
/* @helix. "helix/include/Utils.mqh" */
/* @helix.include " d " */
'''

    # Only lines that actually match Helix patterns
    expected_results = [
        {"include": "helix/include/Calc/Calc.mqh", "directive": None, "replace": None},
        {"include": "../../old.mqh", "directive": "replacewith", "replace": "helix/new.mqh"},
        {"include": "helix/include/Utils.mqh", "directive": "include", "replace": "helix/include/Utils.mqh"},
        {"include": "../../autocomplete/autocomplete.mqh", "directive": None, "replace": None},
        {"include": "../../old.mqh", "directive": "replacewith", "replace": "helix/include/Bar/Bar.mqh"},
        {"include": "../../old.mqh", "directive": "replacewith", "replace": "helix/include/Bar/Bar.mqh"},
        {"include": "helix/include/Utils.mqh", "directive": "include", "replace": "helix/include/Utils.mqh"},
        {"include": "helix/include/Utils.mqh", "directive": "include", "replace": "helix/include/Utils.mqh"},
        {"include": "simple.mqh", "directive": "replacewith", "replace": "novo/caminho.mqh"},
        {"include": " d ", "directive": "include", "replace": " d "},
    ]

    results = [parse_helix_line(line) for line in texto.splitlines() if parse_helix_line(line)]

    assert results == expected_results