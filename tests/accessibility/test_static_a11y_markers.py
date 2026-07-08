"""Static accessibility check tests.

Validates that static HTML assets include WCAG-AA compliant accessibility markers.
"""

from __future__ import annotations

import re
from pathlib import Path


def test_index_html_accessibility_markers() -> None:
    """Scans index.html statically to verify required WCAG-AA markers and semantic structure."""
    html_path = (
        Path(__file__).resolve().parent.parent.parent / "app" / "static" / "index.html"
    )
    assert html_path.exists(), "index.html static asset not found!"

    content = html_path.read_text(encoding="utf-8")

    # 1. Verify HTML lang attribute exists
    assert re.search(r"<html\s+[^>]*lang=", content, re.IGNORECASE) is not None, (
        "HTML element must declare a lang attribute."
    )

    # 2. Skip to Content Link
    assert "skip-link" in content, "Skip-to-content accessibility link is missing."
    assert 'href="#main-content"' in content, (
        "Skip link target must point to #main-content."
    )

    # 3. Main content id matches skip link
    assert 'id="main-content"' in content, (
        "Main layout element is missing id='main-content'."
    )

    # 4. Semantic HTML5 landmarks
    assert "<header" in content, "Header landmark start tag is missing."
    assert "</header>" in content, "Header landmark end tag is missing."
    assert "<nav" in content, "Navigation landmark start tag is missing."
    assert "</nav>" in content, "Navigation landmark end tag is missing."
    assert "<main" in content, "Main landmark start tag is missing."
    assert "</main>" in content, "Main landmark end tag is missing."
    assert "<footer" in content, "Footer landmark start tag is missing."
    assert "</footer>" in content, "Footer landmark end tag is missing."

    # 5. Associated labels for form controls
    # Check all key interactive IDs have associated for labels
    required_labels_for = {
        "language-select",
        "location-select",
        "section-select",
        "arrival-mode-select",
        "kickoff-slider",
        "question-input",
    }
    for control_id in required_labels_for:
        label_pattern = rf'for="{control_id}"'
        assert label_pattern in content, (
            f"Missing <label for='{control_id}'> matching the input control."
        )

    # 6. Checkboxes grouped in fieldset + legend
    assert "<fieldset" in content, "Accessibility Needs fieldset start tag is missing."
    assert "</fieldset>" in content, "Accessibility Needs fieldset end tag is missing."
    assert "<legend" in content, "Fieldset legend start tag is missing."
    assert "</legend>" in content, "Fieldset legend end tag is missing."

    # 7. Live Regions
    assert 'role="log"' in content, "Assistant response region must contain role='log'."
    assert 'aria-live="polite"' in content, (
        "Assistant response region must declare aria-live='polite'."
    )
    assert 'aria-busy="false"' in content, (
        "Assistant response region must declare initial state aria-busy='false'."
    )

    # 8. Noscript fallback
    assert "<noscript" in content, "Noscript start tag is missing."
    assert "</noscript>" in content, "Noscript end tag is missing."
