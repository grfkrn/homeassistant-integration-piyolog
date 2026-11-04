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


def test_resource_registration_ships() -> None:
    frontend_py = (
        ROOT / "custom_components" / "piyolog" / "frontend.py"
    ).read_text(encoding="utf-8")
    assert "async_register_lovelace_resources" in frontend_py
    assert "ResourceStorageCollection" in frontend_py
    assert '"res_type": "module"' in frontend_py


class _FakeResources:
    """Minimal stand-in for ResourceStorageCollection."""

    loaded = True

    def __init__(self) -> None:
        self.items: list[dict] = []
        self.created: list[dict] = []
        self.updated: list[tuple[str, dict]] = []

    def async_items(self) -> list[dict]:
        return list(self.items)

    async def async_load(self) -> None:
        return None

    async def async_create_item(self, data: dict) -> dict:
        item = {
            "id": f"id{len(self.items)}",
            "type": data["res_type"],
            "url": data["url"],
        }
        self.items.append(item)
        self.created.append(data)
        return item

    async def async_update_item(self, item_id: str, updates: dict) -> None:
        self.updated.append((item_id, updates))
        for item in self.items:
            if item["id"] == item_id:
                item.update(updates)


async def test_lovelace_resources_created_updated_idempotent(hass, monkeypatch) -> None:
    import json
    from types import SimpleNamespace

    import homeassistant.components.lovelace.resources as lovelace_resources

    from custom_components.piyolog.frontend import async_register_lovelace_resources

    version = json.loads(
        (ROOT / "custom_components" / "piyolog" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )["version"]
    fake = _FakeResources()
    monkeypatch.setattr(
        lovelace_resources, "ResourceStorageCollection", _FakeResources
    )
    hass.data["lovelace"] = SimpleNamespace(resources=fake)

    await async_register_lovelace_resources(hass)
    assert sorted(item["url"] for item in fake.items) == [
        f"/piyolog_static/piyolog-card.js?v={version}",
        f"/piyolog_static/piyolog-elapsed-card.js?v={version}",
    ]
    assert all(item["type"] == "module" for item in fake.items)

    # Second run: nothing created or updated.
    await async_register_lovelace_resources(hass)
    assert len(fake.created) == 2
    assert fake.updated == []

    # Stale version query: the entry is updated in place, not duplicated.
    fake.items[0]["url"] = "/piyolog_static/piyolog-card.js?v=0.0.0"
    await async_register_lovelace_resources(hass)
    assert len(fake.created) == 2
    assert len(fake.updated) == 1
    assert fake.updated[0][1]["url"].endswith(f"?v={version}")


async def test_lovelace_resources_skipped_safely(hass) -> None:
    from custom_components.piyolog.frontend import async_register_lovelace_resources

    hass.data.pop("lovelace", None)
    await async_register_lovelace_resources(hass)  # must not raise
