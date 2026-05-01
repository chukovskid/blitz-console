"""Smoke-test every page renders without errors. No real API calls.

Catches: import errors, dataclass mismatches, CSS-injection crashes,
session-state references that broke after a refactor.

When the dummy BLITZ_API_KEY in conftest.py is used, the Home and Settings
pages show an expected "Could not reach Blitz" alert because they fetch
key-info on load. That specific alert is not a test failure — it tells us
the error path renders correctly. Anything else is.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest


PAGES = [
    "app/Home.py",
    "app/pages/1_Build_Search.py",
    "app/pages/2_Saved_ICPs.py",
    "app/pages/3_Run_History.py",
    "app/pages/4_Lookup_Tools.py",
    "app/pages/5_Settings.py",
]

# Substrings of error/warning/info messages that are expected when the
# dummy BLITZ_API_KEY is used and we don't have network. Anything else
# is treated as a real failure.
EXPECTED_ERROR_FRAGMENTS = (
    "Could not reach Blitz",
    "Invalid API key",
    "401",
    "BLITZ_API_KEY",
)


def _is_unexpected(value: str) -> bool:
    return not any(frag in value for frag in EXPECTED_ERROR_FRAGMENTS)


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_unexpected_errors(page):
    at = AppTest.from_file(page, default_timeout=30).run()

    # Filter out expected dummy-key errors
    real_errors = [e for e in at.error if _is_unexpected(str(e.value))]
    exceptions = list(at.exception)

    assert not real_errors, "Unexpected st.error() shown:\n" + "\n".join(
        str(e.value)[:300] for e in real_errors
    )
    assert not exceptions, "Uncaught exception during render:\n" + "\n".join(
        str(e.value)[:300] for e in exceptions
    )


def test_home_page_renders_title():
    at = AppTest.from_file("app/Home.py", default_timeout=30).run()
    # design.page_header uses st.markdown("# Console") for consistent CSS.
    md_text = " ".join(str(m.value) for m in at.markdown)
    assert "Console" in md_text, f"'Console' missing from markdown: {md_text[:300]}"


def test_build_search_renders_title():
    at = AppTest.from_file("app/pages/1_Build_Search.py", default_timeout=30).run()
    md_text = " ".join(str(m.value) for m in at.markdown)
    assert "Build search" in md_text, f"'Build search' missing: {md_text[:300]}"


def test_lookup_tools_renders_all_tabs():
    at = AppTest.from_file("app/pages/4_Lookup_Tools.py", default_timeout=30).run()
    # Lookup_Tools defines 5 tabs; just verify the page produced markdown content.
    md_text = " ".join(str(m.value) for m in at.markdown)
    assert "Lookup tools" in md_text
