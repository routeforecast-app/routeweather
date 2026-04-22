from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import select

from app.models import SupportAuditLog, User


def _registration_payload(email: str, password: str, *, first_name: str = "Test", last_name: str = "User", phone_number: str = "+447700900123") -> dict[str, str]:
    return {
        "first_name": first_name,
        "last_name": last_name,
        "phone_number": phone_number,
        "email": email,
        "password": password,
    }


def test_user_self_deactivation_is_cancelled_by_login(client, db_session):
    register_response = client.post(
        "/auth/register",
        json=_registration_payload("selfdeactivate@example.com", "supersecure123"),
    )
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    deactivate_response = client.post("/users/me/deactivate", headers=headers)
    assert deactivate_response.status_code == 200

    user = db_session.exec(select(User).where(User.email == "selfdeactivate@example.com")).first()
    assert user is not None
    assert user.account_status == "user_deactivated"
    assert user.scheduled_deletion_at is not None

    login_response = client.post(
        "/auth/login",
        json={"email": "selfdeactivate@example.com", "password": "supersecure123"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["account_status"] == "active"


def test_admin_deactivated_user_stays_blocked_until_reactivated(client):
    system_manager_response = client.post(
        "/auth/register",
        json=_registration_payload("Jack.s.steele2007@icloud.com", "StrongPass1!"),
    )
    system_manager_headers = {"Authorization": f"Bearer {system_manager_response.json()['access_token']}"}

    support_response = client.post(
        "/auth/register",
        json=_registration_payload("support@example.com", "supersecure123"),
    )
    support_headers = {"Authorization": f"Bearer {support_response.json()['access_token']}"}
    client.post(
        "/users/admin/role-grants",
        headers=system_manager_headers,
        json={"email": "support@example.com", "role": "support_user"},
    )

    client.post("/auth/register", json=_registration_payload("blocked@example.com", "supersecure123"))

    deactivate_response = client.post(
        "/support/admin-deactivate",
        headers=system_manager_headers,
        json={
            "email": "blocked@example.com",
            "confirm_email": "blocked@example.com",
            "reason": "Breach of terms under review.",
        },
    )
    assert deactivate_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={"email": "blocked@example.com", "password": "supersecure123"},
    )
    assert login_response.status_code == 200
    blocked_token = login_response.json()["access_token"]
    assert login_response.json()["user"]["account_status"] == "admin_deactivated"

    routes_response = client.get("/routes", headers={"Authorization": f"Bearer {blocked_token}"})
    assert routes_response.status_code == 403
    assert "deactivated by an administrator" in routes_response.json()["detail"].lower()

    forbidden_support_reactivate = client.post(
        "/support/reactivate",
        headers=support_headers,
        json={"email": "blocked@example.com", "confirm_email": "blocked@example.com", "reason": "Support check"},
    )
    assert forbidden_support_reactivate.status_code == 403

    reactivate_response = client.post(
        "/support/reactivate",
        headers=system_manager_headers,
        json={"email": "blocked@example.com", "confirm_email": "blocked@example.com", "reason": "Appeal accepted"},
    )
    assert reactivate_response.status_code == 200

    restored_login_response = client.post(
        "/auth/login",
        json={"email": "blocked@example.com", "password": "supersecure123"},
    )
    assert restored_login_response.status_code == 200
    assert restored_login_response.json()["user"]["account_status"] == "active"


def test_inactive_accounts_feed_shows_auto_deactivated_and_deleted_accounts(client, db_session):
    system_manager_response = client.post(
        "/auth/register",
        json=_registration_payload("Jack.s.steele2007@icloud.com", "StrongPass1!"),
    )
    system_manager_headers = {"Authorization": f"Bearer {system_manager_response.json()['access_token']}"}
    client.post(
        "/users/admin/role-grants",
        headers=system_manager_headers,
        json={"email": "support@example.com", "role": "support_user"},
    )
    support_response = client.post(
        "/auth/register",
        json=_registration_payload("support@example.com", "supersecure123"),
    )
    support_headers = {"Authorization": f"Bearer {support_response.json()['access_token']}"}

    client.post("/auth/register", json=_registration_payload("inactive@example.com", "supersecure123"))

    user = db_session.exec(select(User).where(User.email == "inactive@example.com")).first()
    assert user is not None
    now = datetime.now(timezone.utc)
    user.last_active_at = now - timedelta(days=366)
    user.last_login_at = now - timedelta(days=366)
    db_session.add(user)
    db_session.commit()

    first_feed_response = client.get("/support/inactive-accounts", headers=support_headers)
    assert first_feed_response.status_code == 200
    first_feed = first_feed_response.json()
    inactive_account = next(item for item in first_feed if item["email"] == "inactive@example.com")
    assert inactive_account["status_label"] == "Deactivated"
    assert inactive_account["account_status"] == "inactive_deactivated"

    user = db_session.exec(select(User).where(User.email == "inactive@example.com")).first()
    assert user is not None
    user.scheduled_deletion_at = now - timedelta(days=1)
    db_session.add(user)
    db_session.commit()

    second_feed_response = client.get("/support/inactive-accounts", headers=support_headers)
    assert second_feed_response.status_code == 200
    second_feed = second_feed_response.json()
    deleted_account = next(item for item in second_feed if item["email"] == "inactive@example.com")
    assert deleted_account["status_label"] == "Deleted"
    assert deleted_account["account_status"] == "deleted"


def test_admin_permanent_delete_requires_password_and_records_deleted_account(client, db_session):
    system_manager_response = client.post(
        "/auth/register",
        json=_registration_payload("Jack.s.steele2007@icloud.com", "StrongPass1!"),
    )
    system_manager_headers = {"Authorization": f"Bearer {system_manager_response.json()['access_token']}"}

    client.post("/auth/register", json=_registration_payload("delete-me@example.com", "supersecure123"))

    bad_delete_response = client.post(
        "/support/admin-delete",
        headers=system_manager_headers,
        json={
            "email": "delete-me@example.com",
            "confirm_email": "delete-me@example.com",
            "admin_password": "WrongPass1!",
        },
    )
    assert bad_delete_response.status_code == 400

    delete_response = client.post(
        "/support/admin-delete",
        headers=system_manager_headers,
        json={
            "email": "delete-me@example.com",
            "confirm_email": "delete-me@example.com",
            "admin_password": "StrongPass1!",
        },
    )
    assert delete_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={"email": "delete-me@example.com", "password": "supersecure123"},
    )
    assert login_response.status_code == 401

    inactive_feed_response = client.get("/support/inactive-accounts", headers=system_manager_headers)
    assert inactive_feed_response.status_code == 200
    deleted_account = next(item for item in inactive_feed_response.json() if item["email"] == "delete-me@example.com")
    assert deleted_account["status_label"] == "Deleted"

    audit_logs = db_session.exec(select(SupportAuditLog).where(SupportAuditLog.action == "admin_delete_account_requested")).all()
    assert audit_logs
