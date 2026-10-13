def test_list_recipes_empty(client):
    response = client.get("/api/v1/recipes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data == [], f"Expected empty list but got {len(data)} recipe(s) — test isolation may be broken"


def test_list_recipes_after_job(client):
    client.post("/api/v1/jobs", json={"source_url": "https://example.com/recipe-list-test"})

    response = client.get("/api/v1/recipes")
    assert response.status_code == 200
    recipes = response.json()
    assert len(recipes) >= 1


def test_get_recipe_not_found(client):
    response = client.get("/api/v1/recipes/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_get_recipe_structure(client):
    job_response = client.post(
        "/api/v1/jobs", json={"source_url": "https://example.com/structure-test"}
    )
    job_id = job_response.json()["job_id"]

    import time
    for _ in range(10):
        poll = client.get(f"/api/v1/jobs/{job_id}")
        if poll.json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    recipe_id = poll.json()["recipe_id"]
    response = client.get(f"/api/v1/recipes/{recipe_id}")
    assert response.status_code == 200

    recipe = response.json()
    # Required fields present
    assert "id" in recipe
    assert "job_id" in recipe
    assert "title" in recipe
    assert "ingredients" in recipe
    assert "equipment" in recipe
    assert "steps" in recipe
    assert "calories" in recipe
    assert "protein_g" in recipe
    assert "carbs_g" in recipe
    assert "fat_g" in recipe
    assert "created_at" in recipe

    # Ingredient objects are structured
    assert len(recipe["ingredients"]) > 0
    first = recipe["ingredients"][0]
    assert "name" in first
    assert "quantity" in first

    # Lists are non-empty
    assert len(recipe["steps"]) > 0
    assert len(recipe["equipment"]) > 0


def test_list_recipes_pagination(client):
    # Create two jobs
    client.post("/api/v1/jobs", json={"source_url": "https://example.com/pag1"})
    client.post("/api/v1/jobs", json={"source_url": "https://example.com/pag2"})

    all_recipes = client.get("/api/v1/recipes?limit=100").json()
    one = client.get("/api/v1/recipes?limit=1").json()
    assert len(one) == 1
    assert len(all_recipes) >= len(one)
