# tests/test_include_parser.py
import pytest

# ----------------------------------------------------------------------
# Helix directive parser – uses the new @helix:<directive> syntax
# ----------------------------------------------------------------------
from helix.commands.install import _resolve_includes_pattern as pattern

def parse_helix_line(line: str):
    """
    Parse a line containing a Helix directive using the original regex.

    Returns:
        dict with keys: "include", "directive", "replace"
        or None if the line does not match any supported Helix pattern.
    """
    m = pattern.match(line)
    if not m:
        return None

    include_path = m.group('include')
    directive    = m.group('directive1') or m.group('directive2')
    replace_path = m.group('path1') or m.group('path2')

    # Special case: standalone /* @helix:include "file.mqh" */
    # → this means "this file should be included instead"
    if include_path is None and directive == "include":
        include_path = replace_path

    return {
        "include":   include_path,   # the actual file being included (after resolution)
        "directive": directive,      # e.g. "replace-with", "include", None
        "replace":   replace_path,   # path from the @helix: directive (if any)
    }


# ----------------------------------------------------------------------
# Individual test cases – covers all realistic variations
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "line, expected",
    [
        # 1. Simple #include – no Helix directive
        (
            '#include "helix/include/Calc/Calc.mqh"',
            {"include": "helix/include/Calc/Calc.mqh", "directive": None, "replace": None},
        ),
        # 2. #include + @helix:replace-with (with spaces)
        (
            '#include "../../old.mqh" /* @helix:replace-with "helix/new.mqh" */',
            {"include": "../../old.mqh", "directive": "replace-with", "replace": "helix/new.mqh"},
        ),
        # 3. Standalone include directive
        (
            '/* @helix:include "helix/include/Utils.mqh" */',
            {"include": "helix/include/Utils.mqh", "directive": "include", "replace": "helix/include/Utils.mqh"},
        ),
        # 4. Normal include, no directive
        (
            '#include "../../autocomplete/autocomplete.mqh"',
            {"include": "../../autocomplete/autocomplete.mqh", "directive": None, "replace": None},
        ),
        # 5. Glued comment (no space before /*)
        (
            '#include "../../old.mqh" /*@helix:replace-with "helix/include/Bar/Bar.mqh"*/',
            {"include": "../../old.mqh", "directive": "replace-with", "replace": "helix/include/Bar/Bar.mqh"},
        ),
        # 6. Fully glued extreme case – NOT supported by current regex → expected None
        (
            '#include"../../old.mqh"/*@helix:replace-with"helix/include/Bar/Bar.mqh"*/',
            None,
        ),
        # 7. Glued standalone directive
        (
            '/*@helix:include "helix/include/Utils.mqh"*/',
            {"include": "helix/include/Utils.mqh", "directive": "include", "replace": "helix/include/Utils.mqh"},
        ),
        # 8. With extra whitespace/tabs
        (
            '#include "simple.mqh"     /* @helix:replace-with "novo/caminho.mqh" */',
            {"include": "simple.mqh", "directive": "replace-with", "replace": "novo/caminho.mqh"},
        ),
        # 9. Path with spaces inside quotes – must be preserved
        (
            '/* @helix:include "  file with spaces.mqh  " */',
            {"include": "  file with spaces.mqh  ", "directive": "include", "replace": "  file with spaces.mqh  "},
        ),
        # 10. Invalid – missing directive name
        (
            '/* @helix: "something.mqh" */',
            None,
        ),
    ],
)
def test_parse_individual_lines(line, expected):
    """Test parsing of individual lines with various formatting styles."""
    assert parse_helix_line(line) == expected


# ----------------------------------------------------------------------
# Full real-world file block test
# ----------------------------------------------------------------------
def test_full_real_world_block():
    """Test against a complete real file snippet – must match exactly."""
    texto = '''//+------------------------------------------------------------------+
//|                                                   TestScript.mq5 |
//|                                  Copyright 2025, Douglas Rechia. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, MetaQuotes Ltd."
#property link      "https://www.mql5.com"
#property version   "1.00"

#include "helix/include/Calc/Calc.mqh"

#include "../../old.mqh" /* @helix:replace-with "helix/new.mqh" */

/* @helix:include "helix/include/Utils.mqh" */

#include "../../autocomplete/autocomplete.mqh"

#include "../../old.mqh" /* @helix:replace-with "helix/include/Bar/Bar.mqh" */

#include "../../old.mqh" /*@helix:replace-with "helix/include/Bar/Bar.mqh"*/

/* @helix:include "helix/include/Utils.mqh" */

/*@helix:include "helix/include/Utils.mqh"*/

#include "simple.mqh"     /* @helix:replace-with "novo/caminho.mqh" */

/* @helix: "helix/include/Utils.mqh" */

/* @helix:include " d " */

'''

    expected_results = [
        {"include": "helix/include/Calc/Calc.mqh", "directive": None, "replace": None},
        {"include": "../../old.mqh", "directive": "replace-with", "replace": "helix/new.mqh"},
        {"include": "helix/include/Utils.mqh", "directive": "include", "replace": "helix/include/Utils.mqh"},
        {"include": "../../autocomplete/autocomplete.mqh", "directive": None, "replace": None},
        {"include": "../../old.mqh", "directive": "replace-with", "replace": "helix/include/Bar/Bar.mqh"},
        {"include": "../../old.mqh", "directive": "replace-with", "replace": "helix/include/Bar/Bar.mqh"},
        {"include": "helix/include/Utils.mqh", "directive": "include", "replace": "helix/include/Utils.mqh"},
        {"include": "helix/include/Utils.mqh", "directive": "include", "replace": "helix/include/Utils.mqh"},
        {"include": "simple.mqh", "directive": "replace-with", "replace": "novo/caminho.mqh"},
        {"include": " d ", "directive": "include", "replace": " d "},
    ]

    results = [
        parse_helix_line(line)
        for line in texto.splitlines()
        if parse_helix_line(line) is not None
    ]

    assert results == expected_results