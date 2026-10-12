from app.schemas.recipe import RecipeSchema
from app.services.llm.mock import MockRecipeExtractor


def test_mock_extractor_returns_recipe_schema():
    extractor = MockRecipeExtractor()
    result = extractor.extract("any transcript text")
    assert isinstance(result, RecipeSchema)


def test_mock_extractor_title_is_non_empty():
    extractor = MockRecipeExtractor()
    result = extractor.extract("any transcript text")
    assert result.title and len(result.title) > 0


def test_mock_extractor_ingredients_are_structured():
    extractor = MockRecipeExtractor()
    result = extractor.extract("any transcript text")
    assert len(result.ingredients) > 0
    for ingredient in result.ingredients:
        assert hasattr(ingredient, "name")
        assert hasattr(ingredient, "quantity")
        assert isinstance(ingredient.name, str)
        assert isinstance(ingredient.quantity, str)


def test_mock_extractor_has_steps_and_equipment():
    extractor = MockRecipeExtractor()
    result = extractor.extract("any transcript text")
    assert len(result.steps) > 0
    assert len(result.equipment) > 0


def test_mock_extractor_has_nutrition():
    extractor = MockRecipeExtractor()
    result = extractor.extract("any transcript text")
    assert result.calories is not None
    assert result.protein_g is not None
    assert result.carbs_g is not None
    assert result.fat_g is not None


def test_mock_extractor_ignores_transcript_content():
    extractor = MockRecipeExtractor()
    result_a = extractor.extract("transcript one")
    result_b = extractor.extract("transcript two")
    assert result_a.title == result_b.title
