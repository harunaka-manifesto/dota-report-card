"""Tests for the STRATZ item vocabulary loader and predicates."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.stratz.item_vocabulary import (
    ItemInfo,
    is_consumable,
    is_real_item,
    load_item_vocabulary,
)


@pytest.fixture
def vocab_path() -> Path:
    """Return the path to the committed item vocabulary file."""
    return Path(__file__).resolve().parents[2] / "services" / "api" / "app" / "stratz" / "item_vocabulary.json"


class TestLoadItemVocabulary:
    """Tests for load_item_vocabulary()."""

    def test_loads_file(self, vocab_path: Path) -> None:
        """Vocabulary loads without error."""
        items = load_item_vocabulary(vocab_path)
        assert isinstance(items, dict)
        assert len(items) > 0

    def test_expected_item_count(self, vocab_path: Path) -> None:
        """Vocabulary contains approximately 573 items."""
        items = load_item_vocabulary(vocab_path)
        # Allow for minor fluctuations in the STRATZ API.
        assert 570 <= len(items) <= 580

    def test_items_are_unique_by_id(self, vocab_path: Path) -> None:
        """All item ids are unique."""
        items = load_item_vocabulary(vocab_path)
        ids = list(items.keys())
        assert len(ids) == len(set(ids))

    def test_items_sorted_by_id(self, vocab_path: Path) -> None:
        """Items are stored in deterministic order (by id)."""
        items = load_item_vocabulary(vocab_path)
        ids = list(items.keys())
        assert ids == sorted(ids)

    def test_known_items_present(self, vocab_path: Path) -> None:
        """Known items exist in the vocabulary."""
        items = load_item_vocabulary(vocab_path)
        known_short_names = {
            "blink": "Blink Dagger",
            "tango": "Tango",
            "clarity": "Clarity",
            "black_king_bar": "Black King Bar",
        }
        for short_name, expected_name in known_short_names.items():
            item = next((i for i in items.values() if i.short_name == short_name), None)
            assert item is not None, f"Item {short_name} not found"
            assert item.name == expected_name

    def test_nullable_cost_handled(self, vocab_path: Path) -> None:
        """Items with null cost do not crash the loader."""
        items = load_item_vocabulary(vocab_path)
        # Should have both items with cost and items without.
        with_cost = [i for i in items.values() if i.cost is not None]
        without_cost = [i for i in items.values() if i.cost is None]
        assert len(with_cost) > 0, "No items with cost found"
        assert len(without_cost) > 0, "No items with null cost found"


class TestIsConsumable:
    """Tests for is_consumable()."""

    def test_known_consumables(self) -> None:
        """Known consumables are classified correctly."""
        consumables = [
            ItemInfo(id=73, name="Tango", short_name="tango", cost=90),
            ItemInfo(id=60, name="Clarity", short_name="clarity", cost=60),
            ItemInfo(id=42, name="Smoke of Deceit", short_name="smoke_of_deceit", cost=50),
            ItemInfo(id=45, name="Town Portal Scroll", short_name="tpscroll", cost=100),
        ]
        for item in consumables:
            assert is_consumable(item), f"{item.short_name} should be consumable"

    def test_known_non_consumables(self) -> None:
        """Known non-consumables are not classified as consumables."""
        non_consumables = [
            ItemInfo(id=1, name="Blink Dagger", short_name="blink", cost=2250),
            ItemInfo(id=59, name="Morbid Mask", short_name="mask_of_madness", cost=800),
        ]
        for item in non_consumables:
            assert not is_consumable(item), f"{item.short_name} should not be consumable"


class TestIsRealItem:
    """Tests for is_real_item()."""

    def test_real_items(self) -> None:
        """Expensive items are classified as real items."""
        real_items = [
            ItemInfo(id=1, name="Blink Dagger", short_name="blink", cost=2250),
            ItemInfo(id=45, name="Black King Bar", short_name="black_king_bar", cost=3975),
        ]
        for item in real_items:
            assert is_real_item(item), f"{item.short_name} should be a real item"

    def test_consumables_are_not_real_items_however_expensive(self) -> None:
        """A consumable is excluded on identity, not on price.

        Dust of Appearance costs 180 and Smoke of Deceit 50, so price alone
        would already exclude them; the point of the allowlist is that the rule
        does not depend on that coincidence.
        """
        smoke = ItemInfo(id=188, name="Smoke of Deceit", short_name="smoke_of_deceit", cost=50)
        expensive_consumable = ItemInfo(id=999, name="Fake", short_name="tango", cost=5000)
        assert not is_real_item(smoke)
        assert not is_real_item(expensive_consumable)

    def test_cheap_items_not_real(self) -> None:
        """Items with low cost are not real items."""
        cheap = ItemInfo(id=42, name="Tango", short_name="tango", cost=90)
        assert not is_real_item(cheap), "Cheap items should not be real items"

    def test_null_cost_not_real(self) -> None:
        """Items with null cost are not real items."""
        null_cost = ItemInfo(
            id=999, name="Some Item", short_name="some_item", cost=None
        )
        assert not is_real_item(null_cost), "Items with null cost should not be real items"

    def test_loaded_vocabulary_real_items(self, vocab_path: Path) -> None:
        """Real item classification works on loaded vocabulary."""
        items = load_item_vocabulary(vocab_path)
        real = [i for i in items.values() if is_real_item(i)]
        # Should have a substantial number of real items.
        assert len(real) > 100, f"Expected >100 real items, got {len(real)}"
        # BKB should be among them.
        bkb = next((i for i in real if i.short_name == "black_king_bar"), None)
        assert bkb is not None, "BKB should be a real item"
        assert bkb.cost is not None and bkb.cost >= 500

    def test_loaded_vocabulary_consumables(self, vocab_path: Path) -> None:
        """Consumable classification works on loaded vocabulary."""
        items = load_item_vocabulary(vocab_path)
        consumables = [i for i in items.values() if is_consumable(i)]
        # Should have many consumables.
        assert len(consumables) > 10, f"Expected >10 consumables, got {len(consumables)}"
        # Tango should be among them.
        tango = next((i for i in consumables if i.short_name == "tango"), None)
        assert tango is not None, "Tango should be consumable"


class TestItemInfo:
    """Tests for ItemInfo dataclass."""

    def test_frozen(self) -> None:
        """ItemInfo is frozen and immutable."""
        item = ItemInfo(id=1, name="Test", short_name="test", cost=100)
        with pytest.raises(AttributeError):
            item.id = 2  # type: ignore

    def test_equality(self) -> None:
        """ItemInfo equality is based on all fields."""
        item1 = ItemInfo(id=1, name="Test", short_name="test", cost=100)
        item2 = ItemInfo(id=1, name="Test", short_name="test", cost=100)
        item3 = ItemInfo(id=1, name="Test", short_name="test", cost=200)
        assert item1 == item2
        assert item1 != item3


def test_recipes_are_not_real_items() -> None:
    """A recipe purchase is the same build event as the item it completes.

    Counting both would double-count every build, which would corrupt any
    measurement of when a player's build comes together.
    """
    from app.stratz.item_vocabulary import is_real_item, is_recipe, load_item_vocabulary

    vocabulary = load_item_vocabulary()
    recipes = [item for item in vocabulary.values() if is_recipe(item)]
    assert len(recipes) > 40, "expected the vocabulary to carry many recipes"
    assert all(not is_real_item(item) for item in recipes)
    # Priced above the threshold, so price alone would not have excluded it.
    bkb_recipe = next(i for i in recipes if i.short_name == "recipe_black_king_bar")
    assert bkb_recipe.cost is not None and bkb_recipe.cost >= 500
    assert not is_real_item(bkb_recipe)


def test_bottle_is_a_real_item_not_a_consumable() -> None:
    """Bottle holds an inventory slot all game; its timing is a build milestone."""

    from app.stratz.item_vocabulary import is_consumable, is_real_item, load_item_vocabulary

    bottle = next(
        i for i in load_item_vocabulary().values() if i.short_name == "bottle"
    )
    assert not is_consumable(bottle)
    assert is_real_item(bottle)


def test_the_real_item_set_is_the_expected_size() -> None:
    from app.stratz.item_vocabulary import is_real_item, load_item_vocabulary

    vocabulary = load_item_vocabulary()
    real = [item for item in vocabulary.values() if is_real_item(item)]
    # 215 before recipes were excluded and bottle was reclassified.
    assert 150 <= len(real) <= 200
