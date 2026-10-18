"""
tests/test_custom_css.py

Guards the design-system CSS against the three bug classes that
previously shipped silently:

  1. Broken selector typos (`#wc.app` / `.wc.page` instead of
     `#wc-app` / `.wc-page`) — CSS fails silently, so a typo here
     disabled every light-theme override at once.
  2. Undefined design tokens — rules using `var(--wc-*)` with no
     matching declaration fall back to raw Bootstrap/DARKLY colors.
  3. Unbalanced braces — a missing brace truncates every rule after it.
"""

import re
from pathlib import Path

import pytest

CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "custom.css"


@pytest.fixture(scope="module")
def css() -> str:
    assert CSS_PATH.exists(), f"missing stylesheet: {CSS_PATH}"
    return CSS_PATH.read_text()


def test_braces_balanced(css):
    assert css.count("{") == css.count("}"), "unbalanced braces in custom.css"


def test_no_broken_selector_typos(css):
    # `#wc.app` / `.wc.page` (dot instead of hyphen) never match — the
    # light theme and page animations were fully disabled by this typo.
    assert "#wc.app" not in css, "found broken selector '#wc.app' (should be '#wc-app')"
    assert ".wc.page" not in css, "found broken selector '.wc.page' (should be '.wc-page')"


def test_all_custom_properties_defined(css):
    used = set(re.findall(r"var\((--wc-[a-z0-9-]+)", css))
    defined = set(re.findall(r"(--wc-[a-z0-9-]+)\s*:", css))
    undefined = used - defined
    assert not undefined, f"custom.css uses undefined tokens: {sorted(undefined)}"


def test_core_theme_tokens_defined(css):
    # Both themes must define the full token set on their scopes.
    scopes = {
        ":root": [
            "--wc-bg", "--wc-surface", "--wc-surface-2", "--wc-text",
            "--wc-muted", "--wc-border", "--wc-primary", "--wc-success",
            "--wc-danger", "--wc-info",
        ],
        "#wc-app[data-theme=\"light\"]": [
            "--wc-bg", "--wc-surface", "--wc-surface-2", "--wc-text",
            "--wc-muted", "--wc-border", "--wc-primary", "--wc-success",
            "--wc-danger", "--wc-info", "--wc-status-warn",
        ],
    }
    for scope, tokens in scopes.items():
        # Match the bare selector followed by "{", not occurrences inside
        # comments or compound selectors (e.g. body:has(...)).
        match = re.search(rf"(^|[{{,;])\s*{re.escape(scope)}\s*\{{", css, re.MULTILINE)
        assert match, f"scope {scope} not found in custom.css"
        block = css[match.start():css.index("}", match.end())]
        for token in tokens:
            assert re.search(rf"{re.escape(token)}\s*:", block), (
                f"{token} missing from scope {scope}"
            )


def test_offcanvas_theme_classes_defined(css):
    # The mobile drawer portals outside #wc-app, so it carries its own
    # wc-theme-dark / wc-theme-light token scopes.
    for cls in (".wc-offcanvas.wc-theme-dark", ".wc-offcanvas.wc-theme-light"):
        assert cls in css, f"missing drawer theme scope: {cls}"
