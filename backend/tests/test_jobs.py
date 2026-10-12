import time


def test_create_job_rejects_empty_url(client):
    response = client.post("/api/v1/jobs", json={"source_url": ""})
    assert response.status_code == 422


def test_create_job_rejects_non_http_url(client):
    response = client.post("/api/v1/jobs", json={"source_url": "ftp://example.com/video"})
    assert response.status_code == 422


def test_create_job_rejects_plain_string(client):
    response = client.post("/api/v1/jobs", json={"source_url": "not-a-url"})
    assert response.status_code == 422


def test_create_job_returns_202(client):
    response = client.post("/api/v1/jobs", json={"source_url": "https://example.com/video1"})
    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["source_url"] == "https://example.com/video1"
    assert data["recipe_id"] is None
    assert data["error_message"] is None


def test_get_job_not_found(client):
    response = client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_get_job_returns_job(client):
    create = client.post("/api/v1/jobs", json={"source_url": "https://example.com/video2"})
    job_id = create.json()["id"]

    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job_id
    assert data["source_url"] == "https://example.com/video2"


def test_job_pipeline_completes(client):
    """
    Full lifecycle test: submit a job, let BackgroundTasks run synchronously
    within the TestClient context, then verify the job is completed and a recipe
    was saved.

    TestClient runs background tasks synchronously before returning the response,
    so we can assert the completed state immediately after the POST.
    """
    response = client.post(
        "/api/v1/jobs", json={"source_url": "https://example.com/chicken-video"}
    )
    assert response.status_code == 202
    job_id = response.json()["id"]

    # Poll the job until it reaches a terminal state (completed or failed).
    # With TestClient, background tasks are synchronous so this should resolve
    # on the first or second poll.
    for _ in range(10):
        poll = client.get(f"/api/v1/jobs/{job_id}")
        status = poll.json()["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert poll.json()["status"] == "completed", (
        f"Job did not complete: {poll.json()}"
    )
    assert poll.json()["recipe_id"] is not None


def test_completed_job_has_accessible_recipe(client):
    response = client.post(
        "/api/v1/jobs", json={"source_url": "https://example.com/pasta-video"}
    )
    job_id = response.json()["id"]

    for _ in range(10):
        poll = client.get(f"/api/v1/jobs/{job_id}")
        if poll.json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    recipe_id = poll.json()["recipe_id"]
    assert recipe_id is not None

    recipe_response = client.get(f"/api/v1/recipes/{recipe_id}")
    assert recipe_response.status_code == 200
    recipe = recipe_response.json()
    assert recipe["title"] == "Lemon Herb Roasted Chicken"
    assert len(recipe["ingredients"]) > 0
    assert "name" in recipe["ingredients"][0]
    assert "quantity" in recipe["ingredients"][0]
