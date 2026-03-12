# knitpkg/mql/manifest_header.py

"""
Generator for knitpkg/build/build_info.mqh.

This module is the single source of truth for how the manifest header file is
built. It is intentionally free of any CLI or I/O concerns: it receives data
and returns a string, making it trivially testable.

Typical call site (inside the compile step)::

    from knitpkg.mql.manifest_header import ManifestHeaderGenerator

    generator = ManifestHeaderGenerator(manifest, cli_defines)
    generator.write(project_dir)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Dict

if TYPE_CHECKING:
    from knitpkg.mql.models import MQLKnitPkgManifest


MANIFEST_HEADER_RELATIVE_PATH = Path("knitpkg") / "build" / "BuildInfo.mqh"

# Manifest fields that can be exported and how to extract their string value.
# Fields whose value is None on the manifest instance are silently skipped.
_FIELD_ACCESSORS = {
    "version":      lambda m: str(m.version),
    "organization": lambda m: str(m.organization),
    "name":         lambda m: str(m.name),
    "description":  lambda m: str(m.description),
    "author":       lambda m: str(m.author)         if m.author      else None, # Optional
    "license":      lambda m: str(m.license)        if m.license     else None, # Optional
    "type":         lambda m: str(m.type),
    "target":       lambda m: str(m.target),
}

def _format_define(name: str, value: Optional[str]) -> str:
    """
    Return a single ``#define`` line.

    * ``value=None``          →  ``#define NAME``
    * numeric string          →  ``#define NAME 42``
    * anything else           →  ``#define NAME "text"``

    The constant name column is padded to 40 characters for readability.
    """
    if value is None:
        return f"#define {name}"
    
    if isinstance(value, bool):
        return f"#define {name:<40} {'true' if value else 'false'}"

    if isinstance(value, int) or isinstance(value, float):
        return f"#define {name:<40} {value}"

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'#define {name:<40} "{escaped}"'


def _make_include_guard(project_descriptor: str) -> str:
    """
    Derive an include-guard symbol from the project name.

    Example: ``"my-project"`` → ``__KNITPKG_MY_PROJECT_BUILDINFO__``
    """
    sanitized = re.sub(r'[^A-Za-z0-9]', '_', project_descriptor).upper()
    return f"__KNITPKG_{sanitized}_BUILDINFO__"


class ManifestHeaderGenerator:
    """
    Builds the content of ``knitpkg/build/BuildInfo.mqh``.

    Parameters
    ----------
    manifest:
        The fully loaded and validated project manifest.
    cli_defines:
        Zero or more :class:`~knitpkg.mql.models.ManifestDefineEntry` objects
        parsed from ``--define`` / ``-D`` CLI arguments. These take the
        highest priority and override any same-named constant from the
        manifest's ``defines`` section.
    """

    def __init__(
        self,
        manifest: "MQLKnitPkgManifest",
        cli_defines: Optional[Dict] = None,
    ) -> None:
        self._manifest    = manifest
        self._cli_defines = cli_defines or {}

    def build(self) -> str:
        """Return the full file content as a string (no I/O performed)."""
        entries = self._resolve_entries()
        return self._render(entries)
    
    def remove(self, project_dir: Path):
        """Delete the manifest header file if it exists."""
        file = (project_dir / MANIFEST_HEADER_RELATIVE_PATH).resolve()
        if file.exists():
            file.unlink()

    def write(self, project_dir: Path) -> Path:
        """
        Write ``BuildInfo.mqh`` under *project_dir*, creating parent
        directories as needed.

        Returns the absolute path of the written file.
        """
        content    = self.build()
        output     = (project_dir / MANIFEST_HEADER_RELATIVE_PATH).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        return output

    def _resolve_entries(self) -> list[tuple[str, Optional[str]]]:
        """
        Merge all define sources into an ordered list of (name, value) pairs,
        respecting priority rules (higher priority wins on name collision):

            1. CLI --define / -D   (highest)
            2. extra               (from manifest 'defines.extra')
            3. from_manifest       (lowest)
        """
        # Collect in reverse priority so that a dict-update later lets higher
        # priority items overwrite lower ones naturally.
        collected: dict[str, Optional[str]] = {}

        # Priority 3 — from_manifest
        if self._manifest.defines and self._manifest.defines.from_manifest:
            for const_name, field_name in self._manifest.defines.from_manifest.items():
                accessor = _FIELD_ACCESSORS.get(field_name)
                if accessor is None:
                    continue
                value = accessor(self._manifest)
                if value is not None:
                    collected[const_name] = value

        # Priority 2 — extra
        if self._manifest.defines and self._manifest.defines.extra:
            for const_name, const_value in self._manifest.defines.extra.items():
                collected[const_name] = const_value

        # Priority 1 — CLI defines (highest; overwrite anything above)
        for name, value in self._cli_defines.items():
            collected[name] = value

        # Preserve insertion order (Python 3.7+ dicts are ordered).
        # Because higher-priority items may overwrite lower-priority ones,
        # we rebuild the list grouping by source for a clean ordering in the
        # final file: from_manifest first, extra second, CLI last.
        return list(collected.items())

    def _render(self, entries: list[tuple[str, Optional[str]]]) -> str:
        """Render the full .mqh file content."""
        guard     = _make_include_guard(f'{self._manifest.organization}_{self._manifest.name}')
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        lines: list[str] = []

        # File header comment
        lines += [
            "// " + "=" * 70,
            "// AUTO-GENERATED BY KNITPKG — DO NOT EDIT MANUALLY",
            f"// Project  : @{self._manifest.organization}/{self._manifest.name}",
            f"// Version  : {self._manifest.version}",
            f"// Generated: {timestamp}",
            "// " + "=" * 70,
            "",
        ]

        # Include guard — open
        lines += [
            f"#ifndef {guard}",
            f"#define {guard}",
            "",
        ]

        if entries:
            for name, value in entries:
                lines.append(_format_define(name, value))
        else:
            lines.append("// No constants defined.")

        # Include guard — close
        lines += [
            "",
            f"#endif // {guard}",
            "",
        ]

        return "\n".join(lines)