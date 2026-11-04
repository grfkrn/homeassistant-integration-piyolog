"""Regression tests for the bundled Lovelace cards (static checks).

The cards are plain JavaScript with no build step; their behavior is
covered by Node-based checks during development. These tests only pin
the integration-side contract: both card files ship in the package and
both are registered as extra JS URLs.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "custom_components" / "piyolog" / "frontend"


def test_elapsed_card_is_bundled_and_registered() -> None:
    frontend_py = (
        ROOT / "custom_components" / "piyolog" / "frontend.py"
    ).read_text(encoding="utf-8")
    assert "piyolog-elapsed-card.js" in frontend_py

    js = (FRONTEND_DIR / "piyolog-elapsed-card.js").read_text(encoding="utf-8")
    # The gauge must read the last-event sensors of both groups.
    for key in (
        "last_pee",
        "last_poop",
        "last_expressed_breast_milk",
        "last_breast_feeding",
        "last_formula",
    ):
        assert key in js
    # Pumping is a different record type and must not feed the gauge.
    assert "last_pumping" not in js
    # User-configurable thresholds and the visual editor ship with it.
    for token in (
        "yellow_after_hours",
        "red_after_hours",
        "max_hours",
        "piyolog-elapsed-card-editor",
        'customElements.define("piyolog-elapsed-card"',
    ):
        assert token in js


def test_timeline_card_still_bundled() -> None:
    js = (FRONTEND_DIR / "piyolog-card.js").read_text(encoding="utf-8")
    assert 'customElements.define("piyolog-card"' in js
