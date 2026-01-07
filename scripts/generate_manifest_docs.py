#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gera docs/knitpkg-manifest.html automaticamente
100% compatível com Pydantic v2 (2.0 até 2.12.5+)
Testado com Pydantic 2.12.5
"""

from typing import List, Dict
from pathlib import Path
from textwrap import dedent
from typing import get_origin, get_args

# Ajuste conforme seu projeto
from knitpkg.core import models

# ===================================================================
# Configuração
# ===================================================================
OUTPUT_FILE = Path("docs/knitpkg-manifest.html")

TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>knitpkg.yaml – KnitPkg Manifest Specification</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <script>hljs.highlightAll();</script>
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; background:#0d1117; color:#c9d1d9; margin:0; padding:0; }}
    .markdown-body {{ box-sizing:border-box; min-width:200px; max-width:980px; margin:40px auto; padding:45px; background:#161b22; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.3); }}
    @media (max-width:767px) {{ .markdown-body {{ padding:20px; margin:20px; }} }}
    pre, code {{ background:#0d1117 !important; border-radius:8px; }}
    h1,h2,h3 {{ color:#58a6ff; border-bottom:1px solid #30363d; padding-bottom:8px; }}
    table {{ width:100%; border-collapse:collapse; margin:20px 0; }}
    th,td {{ border:1px solid #30363d; padding:12px; text-align:left; }}
    th {{ background:#21262d; }}
    .required {{ color:#f85149; }}
    .optional {{ color:#7ee787; }}
    .default {{ font-size:0.9em; color:#a5d6ff; }}
  </style>
</head>
<body>
<article class="markdown-body">
  <h1>knitpkg.yaml – KnitPkg Project Manifest</h1>
  <p><strong>The official configuration file for all KnitPkg-powered projects.</strong></p>
  
  <hr>

  <h2>Fields</h2>
  <table>
    <tr><th>Field</th><th>Required</th><th>Type</th><th>Default</th><th>Description</th></tr>
{FIELDS_TABLE}
  </table>

  <h2>Project Types (<code>type</code>)</h2>
  <ul>
    <li><code>package</code> → Reusable component that other projects can depend on. <strong>MQL4/5 specific: </strong>header-only library (.mqh); allows entrypoints for test scripts (automatically uses <code>flat</code> mode).</li>
    <li><code>mql.expert</code> → MQL4/5 Expert Advisor</li>
    <li><code>mql.indicator</code> → MQL4/5 Custom indicator</li>
    <li><code>mql.script</code> → MQL4/5 Script</li>
    <li><code>mql.library</code> → MQL4/5 library</li>
  </ul>

  <h2>Dependency Formats (supported)</h2>
  <ul>
    <li><code>https://github.com/user/repo.git#v1.2.3</code> → Git + version/tag/branch/commit</li>
    <li><code>file://../my-lib</code> → Local KnitPkg project</li>
    <li><code>./libs/utils</code> or <code>../common</code> → Relative path</li>
  </ul>

  <h2>Full Example</h2>
  <pre><code class="language-yaml">
{EXAMPLE_YAML}
  </code></pre>

  <hr>
  <p style="text-align:center; color:#8b949e; font-size:0.9em;">
    KnitPkg 2025 – The future of MQL5 development
  </p>
</article>
</body>
</html>
"""

# ===================================================================
# Compatibilidade TOTAL com Pydantic v2 (todas as versões)
# ===================================================================
try:
    from pydantic_core import PydanticUndefined  # Pydantic ≥2.8
except ImportError:
    try:
        from pydantic._internal._utils import PydanticUndefined  # versões intermediárias
    except ImportError:
        from pydantic import PydanticUndefined  # versões antigas (2.0-2.7)

from pydantic.fields import FieldInfo


def is_field_required(field: FieldInfo) -> bool:
    if field.default is not PydanticUndefined:
        return False
    if field.default_factory is not None:
        return False
    # Se aceita None → não é required
    origin = get_origin(field.annotation)
    args = get_args(field.annotation)
    if origin is not None and any(a is type(None) for a in args):
        return False
    return True


def get_type_str(field: FieldInfo) -> str:
    origin = get_origin(field.annotation)
    args = get_args(field.annotation)

    if origin in (list, List):
        return "array[string]"
    if origin in (dict, Dict):
        return "object"
    if hasattr(field.annotation, "__name__"):
        return field.annotation.__name__
    return "string"


def get_default_display(field: FieldInfo) -> str:
    if field.default is not PydanticUndefined:
        value = field.default
        if hasattr(value, "value"):  # Enum
            return f"<code>{value.value}</code>"
        return f"<code>{value}</code>"
    if field.default_factory is not None:
        return "<code>{}</code>" if get_type_str(field) == "object" else "<code>null</code>"
    return "—"


def get_field_info(model_class):
    info = []
    for name, field in model_class.model_fields.items():
        required = "Yes" if is_field_required(field) else "No"
        if name == "entrypoints":
            required = "No*"  # exceção especial

        info.append({
            "name": name,
            "required": required,
            "type": get_type_str(field),
            "default": get_default_display(field),
            "desc": (field.description or "").strip() or "—"
        })
    return info


def generate_fields_table():
    fields = get_field_info(models.HelixManifest)
    rows = []
    for f in fields:
        req_class = "required" if "Yes" in f["required"] else "optional"
        row = f'    <tr><td><code>{f["name"]}</code></td><td class="{req_class}">{f["required"]}</td><td>{f["type"]}</td><td>{f["default"]}</td><td>{f["desc"]}</td></tr>'
        rows.append(row)
    return "\n".join(rows)


def generate_example_yaml():
    return dedent("""\
        name: QuantumEA
        version: 3.1.0
        description: Advanced multi-timeframe Expert Advisor
        author: John Trader
        license: MIT
        type: mql.expert
        target: MQL5
        include_mode: flat

        entrypoints:
          - Dependencies.mqh
          - Strategy.mqh
          - QuantumEA.mq5

        dependencies:
          bars: https://github.com/trader/bars.git#v2.1.0
          utils: file://../common/utils
          indicators: ./local/indicators

        dist:
          dist:
            - id: release
              name: QuantumEA-${version}.zip
              items:
                - dependencyId: this
                  src: QuantumEA.mq5
                  dst: Experts/QuantumEA.mq5
        """).strip()


# ===================================================================
# Main
# ===================================================================
def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    html = TEMPLATE.format(
        FIELDS_TABLE=generate_fields_table(),
        EXAMPLE_YAML=generate_example_yaml()
    )
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Documentation generated successfully: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()