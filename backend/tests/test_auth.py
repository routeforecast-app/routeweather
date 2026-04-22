from __future__ import annotations


def _registration_payload(email: str, password: str, *, first_name: str = "Test", last_name: str = "User", phone_number: str = "+447700900123") -> dict[str, str]:
    return {
        "first_name": first_name,
        "last_name": last_name,
        "phone_number": phone_number,
        "email": email,
        "password": password,
    }


def test_register_and_login_flow(client):
    register_response = client.post(
        "/auth/register",
        json=_registration_payload("walker@example.com", "supersecure123", first_name="Wendy", last_name="Walker"),
    )
    assert register_response.status_code == 201
    register_payload = register_response.json()
    assert register_payload["access_token"]
    assert register_payload["user"]["email"] == "walker@example.com"
    assert register_payload["user"]["first_name"] == "Wendy"
    assert register_payload["user"]["role"] == "general_user"

    login_response = client.post(
        "/auth/login",
        json={"email": "walker@example.com", "password": "supersecure123"},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["access_token"]

    me_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {login_payload['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "walker@example.com"
    assert me_response.json()["phone_number"] == "+447700900123"


def test_login_rejects_bad_password(client):
    client.post("/auth/register", json=_registration_payload("hiker@example.com", "supersecure123"))

    response = client.post(
        "/auth/login",
        json={"email": "hiker@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_update_preferences_and_change_password_and_profile(client):
    register_response = client.post(
        "/auth/register",
        json=_registration_payload("preferences@example.com", "supersecure123"),
    )
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile_response = client.patch(
        "/users/me/profile",
        headers=headers,
        json={"first_name": "Paula", "last_name": "Preference", "phone_number": "+447700900999"},
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["first_name"] == "Paula"
    assert profile_response.json()["phone_number"] == "+447700900999"

    preferences_response = client.patch(
        "/users/me/preferences",
        headers=headers,
        json={
            "distance_unit": "miles",
            "temperature_unit": "f",
            "time_format": "12h",
        },
    )
    assert preferences_response.status_code == 200
    assert preferences_response.json()["distance_unit"] == "miles"
    assert preferences_response.json()["temperature_unit"] == "f"
    assert preferences_response.json()["time_format"] == "12h"

    password_response = client.post(
        "/users/me/change-password",
        headers=headers,
        json={"current_password": "supersecure123", "new_password": "newsecure456"},
    )
    assert password_response.status_code == 200

    old_login_response = client.post(
        "/auth/login",
        json={"email": "preferences@example.com", "password": "supersecure123"},
    )
    assert old_login_response.status_code == 401

    new_login_response = client.post(
        "/auth/login",
        json={"email": "preferences@example.com", "password": "newsecure456"},
    )
    assert new_login_response.status_code == 200


def test_forgot_password_returns_generic_message(client):
    response = client.post("/auth/forgot-password", json={"email": "someone@example.com"})
    assert response.status_code == 200
    assert "queued" in response.json()["message"].lower()


def test_seeded_system_manager_email_requires_strong_password(client):
    response = client.post(
        "/auth/register",
        json=_registration_payload("Jack.s.steele2007@icloud.com", "supersecure123"),
    )
    assert response.status_code == 400
    assert "administrator passwords" in response.json()["detail"].lower()


def test_seeded_system_manager_email_gets_highest_access_with_strong_password(client):
    response = client.post(
        "/auth/register",
        json=_registration_payload("Jack.s.steele2007@icloud.com", "StrongPass1!"),
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["user"]["role"] == "system_manager"
    assert payload["user"]["is_admin"] is True
    assert payload["user"]["must_change_password"] is False


def test_system_manager_can_grant_support_role_and_existing_user_is_updated(client):
    system_manager_response = client.post(
        "/auth/register",
        json=_registration_payload("Jack.s.steele2007@icloud.com", "StrongPass1!"),
    )
    system_manager_token = system_manager_response.json()["access_token"]
    system_manager_headers = {"Authorization": f"Bearer {system_manager_token}"}

    user_response = client.post(
        "/auth/register",
        json=_registration_payload("future-support@example.com", "supersecure123"),
    )
    user_token = user_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    create_role_response = client.post(
        "/users/admin/role-grants",
        headers=system_manager_headers,
        json={"email": "future-support@example.com", "role": "support_user"},
    )
    assert create_role_response.status_code == 201
    assert create_role_response.json()["role"] == "support_user"

    me_response = client.get("/users/me", headers=user_headers)
    assert me_response.status_code == 200
    assert me_response.json()["role"] == "support_user"

    support_response = client.get("/support/inactive-accounts", headers=user_headers)
    assert support_response.status_code == 200


def test_admin_password_reset_is_only_forced_on_role_elevation_and_not_every_login(client):
    system_manager_response = client.post(
        "/auth/register",
        json=_registration_payload("Jack.s.steele2007@icloud.com", "StrongPass1!"),
    )
    system_manager_token = system_manager_response.json()["access_token"]
    system_manager_headers = {"Authorization": f"Bearer {system_manager_token}"}

    user_response = client.post(
        "/auth/register",
        json=_registration_payload("promoted-admin@example.com", "supersecure123"),
    )
    user_token = user_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    create_role_response = client.post(
        "/users/admin/role-grants",
        headers=system_manager_headers,
        json={"email": "promoted-admin@example.com", "role": "administration_user"},
    )
    assert create_role_response.status_code == 201

    me_response = client.get("/users/me", headers=user_headers)
    assert me_response.status_code == 200
    assert me_response.json()["role"] == "administration_user"
    assert me_response.json()["must_change_password"] is True

    password_response = client.post(
        "/users/me/change-password",
        headers=user_headers,
        json={"current_password": "supersecure123", "new_password": "StrongerPass1!"},
    )
    assert password_response.status_code == 200

    refreshed_me_response = client.get("/users/me", headers=user_headers)
    assert refreshed_me_response.status_code == 200
    assert refreshed_me_response.json()["must_change_password"] is False

    new_login_response = client.post(
        "/auth/login",
        json={"email": "promoted-admin@example.com", "password": "StrongerPass1!"},
    )
    assert new_login_response.status_code == 200
    assert new_login_response.json()["user"]["must_change_password"] is False
