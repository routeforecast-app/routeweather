from __future__ import annotations


def _registration_payload(email: str, password: str, *, first_name: str = "Test", last_name: str = "User", phone_number: str = "+447700900123") -> dict[str, str]:
    return {
        "first_name": first_name,
        "last_name": last_name,
        "phone_number": phone_number,
        "email": email,
        "password": password,
    }


def _register_user(client, email: str, password: str, **kwargs) -> dict[str, object]:
    response = client.post("/auth/register", json=_registration_payload(email, password, **kwargs))
    assert response.status_code in {200, 201}
    payload = response.json()
    return {
        "token": payload["access_token"],
        "user": payload["user"],
        "headers": {"Authorization": f"Bearer {payload['access_token']}"},
    }


def test_admin_can_track_and_view_visit_analytics(client):
    admin = _register_user(client, "Jack.s.steele2007@icloud.com", "StrongPass1!")

    visit_one = client.post(
        "/analytics/visit",
        json={"path": "/", "timezone": "Europe/London", "language": "en-GB"},
        headers={"x-forwarded-for": "81.2.69.160", "cf-ipcountry": "GB", **admin["headers"]},
    )
    assert visit_one.status_code == 202

    visit_two = client.post(
        "/analytics/visit",
        json={"path": "/upload", "timezone": "America/New_York", "language": "en-US"},
        headers={"x-forwarded-for": "8.8.8.8", "cf-ipcountry": "US"},
    )
    assert visit_two.status_code == 202

    analytics_response = client.get("/analytics/admin/summary", headers=admin["headers"])
    assert analytics_response.status_code == 200
    payload = analytics_response.json()
    assert payload["total_visits"] == 2
    assert payload["unique_visitors"] == 2
    assert any(country["country_code"] == "GB" for country in payload["top_countries"])
    assert any(path["path"] == "/" for path in payload["top_paths"])
    assert payload["recent_visits"]


def test_system_manager_can_remove_non_seeded_role_grant(client):
    system_manager = _register_user(client, "Jack.s.steele2007@icloud.com", "StrongPass1!")
    user = _register_user(client, "removable-support@example.com", "supersecure123")

    create_response = client.post(
        "/users/admin/role-grants",
        headers=system_manager["headers"],
        json={"email": "removable-support@example.com", "role": "support_user"},
    )
    assert create_response.status_code == 201
    role_grant_id = create_response.json()["id"]

    before_response = client.get("/users/me", headers=user["headers"])
    assert before_response.status_code == 200
    assert before_response.json()["role"] == "support_user"

    delete_response = client.delete(f"/users/admin/role-grants/{role_grant_id}", headers=system_manager["headers"])
    assert delete_response.status_code == 200

    after_response = client.get("/users/me", headers=user["headers"])
    assert after_response.status_code == 200
    assert after_response.json()["role"] == "general_user"


def test_seeded_system_manager_grant_cannot_be_removed(client):
    system_manager = _register_user(client, "Jack.s.steele2007@icloud.com", "StrongPass1!")

    grants_response = client.get("/users/admin/role-grants", headers=system_manager["headers"])
    assert grants_response.status_code == 200
    seeded_grant = next(item for item in grants_response.json() if item["email"] == "jack.s.steele2007@icloud.com")
    assert seeded_grant["is_seeded"] is True

    delete_response = client.delete(
        f"/users/admin/role-grants/{seeded_grant['id']}",
        headers=system_manager["headers"],
    )
    assert delete_response.status_code == 400
