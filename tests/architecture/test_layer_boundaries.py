"""Architectural boundary checks.

Asserts that flow_engine modules have zero imports of the LLM client or phrasing layer.
"""

from __future__ import annotations

import ast
from pathlib import Path


def test_flow_engine_zero_llm_imports() -> None:
    """Statically scans flow_engine modules to ensure strict layer boundary isolation."""
    # Find the services/flow_engine directory
    flow_engine_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "app"
        / "services"
        / "flow_engine"
    )
    assert flow_engine_dir.exists(), "flow_engine service directory not found!"

    forbidden_imports = {
        "llm_client",
        "llm_phraser",
        "phrasing",
        "google.generativeai",
    }

    # Scan python files
    py_files = list(flow_engine_dir.glob("**/*.py"))
    assert len(py_files) > 0, "No Python modules found in flow_engine!"

    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            # Check import statement: import x
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    for forbidden in forbidden_imports:
                        if forbidden in name:
                            raise AssertionError(
                                f"Architectural Violation: Forbidden import '{name}' "
                                f"found in {file_path.name}"
                            )
            # Check import statement: from x import y
            elif isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
                for forbidden in forbidden_imports:
                    if forbidden in module:
                        raise AssertionError(
                            f"Architectural Violation: Forbidden import 'from {module}' "
                            f"found in {file_path.name}"
                        )
