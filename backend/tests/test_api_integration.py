from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_login_endpoint_returns_token():
    response = client.post(
        "/api/auth/login",
        json={"email": "candidate@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token"]
    assert body["user"]["email"] == "candidate@example.com"


def test_profile_updates_persist():
    response = client.put(
        "/api/profile",
        json={"name": "Updated Name", "title": "Senior Designer", "email": "updated@example.com", "location": "Paris"},
    )
    assert response.status_code == 200
    assert response.json()["profile"]["name"] == "Updated Name"

    profile_response = client.get("/api/profile")
    assert profile_response.status_code == 200
    assert profile_response.json()["name"] == "Updated Name"
