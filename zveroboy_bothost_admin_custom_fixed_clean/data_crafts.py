"""Большой банк рецептов крафта и объединения."""

from __future__ import annotations

from typing import Any

from data_items import ITEMS, category_items, get_item

RECIPES: dict[int, dict[str, Any]] = {}


def add_recipe(recipe_id: int, name: str, result: int, result_amount: int, ingredients: dict[int, int], *, station: str = "craft", required_level: int = 1) -> None:
    RECIPES[recipe_id] = {
        "id": recipe_id,
        "name": name,
        "result": result,
        "result_amount": result_amount,
        "ingredients": ingredients,
        "station": station,
        "required_level": required_level,
    }


foods = category_items("food")
materials = category_items("material")
equipment = category_items("equipment")
elixirs = category_items("elixir")
scrolls = category_items("scroll")
recipes = category_items("recipe")

rid = 1
# Еда.
for i, out in enumerate(foods[:70]):
    ing = {
        materials[i % len(materials)]: 2 + i % 3,
        materials[(i + 5) % len(materials)]: 1 + (i % 2),
    }
    add_recipe(rid, f"Кухня #{rid}", out, 1 + (1 if i % 9 == 0 else 0), ing, station="kitchen", required_level=1 + i // 8)
    rid += 1

# Экипировка.
for i, out in enumerate(equipment[:70]):
    ing = {
        materials[(i + 1) % len(materials)]: 2 + i % 3,
        materials[(i + 8) % len(materials)]: 2 + (i + 1) % 3,
        materials[(i + 13) % len(materials)]: 1 + (i % 2),
    }
    add_recipe(rid, f"Кузня #{rid}", out, 1, ing, station="forge", required_level=3 + i // 5)
    rid += 1

# Эликсиры.
for i, out in enumerate(elixirs[:70]):
    ing = {
        materials[(i + 2) % len(materials)]: 2 + i % 2,
        materials[(i + 6) % len(materials)]: 1 + (i % 3),
        foods[i % len(foods)]: 1,
    }
    add_recipe(rid, f"Алхимия #{rid}", out, 1, ing, station="alchemy", required_level=2 + i // 6)
    rid += 1

# Свитки.
for i, out in enumerate(scrolls[:70]):
    ing = {
        materials[(i + 4) % len(materials)]: 2 + i % 3,
        materials[(i + 9) % len(materials)]: 1 + (i % 2),
        recipes[i % len(recipes)]: 1,
    }
    add_recipe(rid, f"Руны #{rid}", out, 1, ing, station="scribe", required_level=4 + i // 5)
    rid += 1

# Переплавка материалов вверх по редкости.
mat_sorted = sorted(materials)
for i in range(0, len(mat_sorted) - 1):
    src = mat_sorted[i]
    dst = mat_sorted[(i + 1) % len(mat_sorted)]
    add_recipe(rid, f"Переплавка #{rid}", dst, 1, {src: 4, mat_sorted[(i + 2) % len(mat_sorted)]: 1}, station="forge", required_level=1 + i // 4)
    rid += 1

# Объединения предметов ради паков.
for i in range(30):
    add_recipe(rid, f"Набор питания #{rid}", foods[(i * 2) % len(foods)], 2, {
        foods[(i + 1) % len(foods)]: 1,
        materials[(i + 3) % len(materials)]: 2,
        materials[(i + 5) % len(materials)]: 1,
    }, station="kitchen", required_level=2 + i // 6)
    rid += 1

for i in range(30):
    add_recipe(rid, f"Набор алхимика #{rid}", elixirs[(i * 2) % len(elixirs)], 2, {
        elixirs[(i + 1) % len(elixirs)]: 1,
        materials[(i + 6) % len(materials)]: 2,
        foods[(i + 4) % len(foods)]: 1,
    }, station="alchemy", required_level=3 + i // 6)
    rid += 1

# Эпические комбинации и коллекционные рецепты.
for i in range(40):
    add_recipe(rid, f"Легендарная сборка #{rid}", equipment[(i + 25) % len(equipment)], 1, {
        equipment[(i + 5) % len(equipment)]: 1,
        materials[(i + 11) % len(materials)]: 3,
        elixirs[(i + 7) % len(elixirs)]: 1,
        recipes[(i + 2) % len(recipes)]: 1,
    }, station="forge", required_level=10 + i // 2)
    rid += 1

# Универсальные обмены ради гибкой экономики.
while rid <= 320:
    a = materials[(rid * 3) % len(materials)]
    b = materials[(rid * 5) % len(materials)]
    out = foods[rid % len(foods)] if rid % 2 == 0 else elixirs[rid % len(elixirs)]
    add_recipe(rid, f"Универсальный рецепт #{rid}", out, 1 + (1 if rid % 7 == 0 else 0), {a: 2, b: 2}, station="craft", required_level=1 + rid // 25)
    rid += 1


def recipes_for_result(item_id: int) -> list[dict[str, Any]]:
    return [recipe for recipe in RECIPES.values() if recipe["result"] == item_id]


def recipe_lines(recipe: dict[str, Any]) -> list[str]:
    lines = []
    for item_id, amount in recipe["ingredients"].items():
        item = get_item(item_id)
        lines.append(f"• {item['emoji']} {item['name']} x{amount} [{item_id}]")
    return lines
