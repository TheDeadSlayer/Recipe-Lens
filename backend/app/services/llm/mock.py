from app.schemas.recipe import Ingredient, RecipeSchema
from app.services.llm.base import RecipeExtractor

_MOCK_RECIPE = RecipeSchema(
    title="Lemon Herb Roasted Chicken",
    ingredients=[
        Ingredient(name="Whole chicken", quantity="1.5 kg"),
        Ingredient(name="Lemon", quantity="2"),
        Ingredient(name="Garlic cloves", quantity="4"),
        Ingredient(name="Fresh rosemary", quantity="1 handful"),
        Ingredient(name="Fresh thyme", quantity="1 handful"),
        Ingredient(name="Olive oil", quantity="2 tbsp"),
        Ingredient(name="Salt", quantity="to taste"),
        Ingredient(name="Black pepper", quantity="to taste"),
    ],
    equipment=[
        "Oven",
        "Roasting tin",
        "Small mixing bowl",
        "Paper towels",
        "Knife",
    ],
    steps=[
        "Preheat oven to 200°C.",
        "Pat the chicken dry with paper towels.",
        "Zest one lemon and juice both lemons.",
        "Crush the garlic cloves.",
        "Mix olive oil, lemon zest, lemon juice, garlic, rosemary, and thyme in a bowl.",
        "Season the mixture with salt and pepper.",
        "Rub the mixture all over the chicken, including under the breast skin.",
        "Place the chicken breast-side up in a roasting tin.",
        "Roast for 80 minutes (20 min per 500 g plus 20 min extra).",
        "Rest for 10 minutes before carving.",
    ],
    calories=350,
    protein_g=42.0,
    carbs_g=2.0,
    fat_g=18.0,
)


class MockRecipeExtractor(RecipeExtractor):
    """Returns a hardcoded recipe fixture. No external calls."""

    def extract(self, transcript: str) -> RecipeSchema:  # noqa: ARG002
        return _MOCK_RECIPE
