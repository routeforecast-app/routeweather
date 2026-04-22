from __future__ import annotations

from pathlib import Path

from sqlmodel import select

from app.config import get_settings
from app.models import SupportAuditLog, User
from app.utils.security import encrypt_sensitive_value


def _registration_payload(email: str, password: str, *, first_name: str = "Test", last_name: str = "User", phone_number: str = "+447700900123") -> dict[str, str]:
    return {
        "first_name": first_name,
        "last_name": last_name,
        "phone_number": phone_number,
        "email": email,
        "password": password,
    }


def test_support_user_can_queue_password_reset_after_identity_check(client, db_session):
    system_manager_response = client.post(
        "/auth/register",
        json=_registration_payload("Jack.s.steele2007@icloud.com", "StrongPass1!", first_name="Jack", last_name="Steele"),
    )
    system_manager_headers = {"Authorization": f"Bearer {system_manager_response.json()['access_token']}"}

    client.post(
        "/users/admin/role-grants",
        headers=system_manager_headers,
        json={"email": "support@example.com", "role": "support_user"},
    )
    support_response = client.post(
        "/auth/register",
        json=_registration_payload("support@example.com", "supersecure123", first_name="Sam", last_name="Support"),
    )
    support_headers = {"Authorization": f"Bearer {support_response.json()['access_token']}"}

    client.post(
        "/auth/register",
        json=_registration_payload("recover@example.com", "supersecure123", first_name="Riley", last_name="Recover"),
    )

    reset_response = client.post(
        "/support/password-reset",
        headers=support_headers,
        json={"email": "recover@example.com", "first_name": "Riley", "last_name": "Recover"},
    )
    assert reset_response.status_code == 200

    logs = db_session.exec(select(SupportAuditLog).where(SupportAuditLog.target_email == "recover@example.com")).all()
    assert any(log.action == "support_password_reset_requested" for log in logs)


def test_senior_support_can_search_accounts_change_email_and_view_audit_logs(client, db_session):
    settings = get_settings()
    outbox_before = {path.name for path in Path(settings.email_outbox_dir).glob("*.json")}

    system_manager_response = client.post(
        "/auth/register",
        json=_registration_payload("Jack.s.steele2007@icloud.com", "StrongPass1!", first_name="Jack", last_name="Steele"),
    )
    system_manager_headers = {"Authorization": f"Bearer {system_manager_response.json()['access_token']}"}

    client.post(
        "/users/admin/role-grants",
        headers=system_manager_headers,
        json={"email": "senior@example.com", "role": "senior_support_user"},
    )
    senior_support_response = client.post(
        "/auth/register",
        json=_registration_payload("senior@example.com", "supersecure123", first_name="Sonia", last_name="Senior"),
    )
    senior_support_headers = {"Authorization": f"Bearer {senior_support_response.json()['access_token']}"}

    target_response = client.post(
        "/auth/register",
        json=_registration_payload("old-email@example.com", "supersecure123", first_name="Casey", last_name="Caller", phone_number="+447700900555"),
    )
    target_user_id = target_response.json()["user"]["id"]

    search_response = client.post(
        "/support/account-search",
        headers=senior_support_headers,
        json={"first_name": "Casey", "last_name": "Caller", "phone_number": "+447700900555"},
    )
    assert search_response.status_code == 200
    matches = search_response.json()
    assert len(matches) == 1
    assert matches[0]["user_id"] == target_user_id
    assert matches[0]["paid_member_status"] == "Not paid"

    change_response = client.post(
        "/support/email-change",
        headers=senior_support_headers,
        json={"user_id": target_user_id, "new_email": "new-email@example.com"},
    )
    assert change_response.status_code == 200

    user = db_session.exec(select(User).where(User.id == target_user_id)).first()
    assert user is not None
    assert user.email == "new-email@example.com"

    audit_response = client.get("/support/audit-logs", headers=senior_support_headers)
    assert audit_response.status_code == 200
    assert any(log["action"] == "account_email_changed_for_recovery" for log in audit_response.json())

    outbox_after = {path.name for path in Path(settings.email_outbox_dir).glob("*.json")}
    assert len(outbox_after) >= len(outbox_before) + 2


def test_senior_support_search_returns_all_matching_accounts_including_legacy_formatting(client, db_session):
    system_manager_response = client.post(
        "/auth/register",
        json=_registration_payload("Jack.s.steele2007@icloud.com", "StrongPass1!", first_name="Jack", last_name="Steele"),
    )
    system_manager_headers = {"Authorization": f"Bearer {system_manager_response.json()['access_token']}"}

    client.post(
        "/users/admin/role-grants",
        headers=system_manager_headers,
        json={"email": "senior2@example.com", "role": "senior_support_user"},
    )
    senior_support_response = client.post(
        "/auth/register",
        json=_registration_payload("senior2@example.com", "supersecure123", first_name="Sonia", last_name="Senior"),
    )
    senior_support_headers = {"Authorization": f"Bearer {senior_support_response.json()['access_token']}"}

    first_target_response = client.post(
        "/auth/register",
        json=_registration_payload("match-one@example.com", "supersecure123", first_name="Casey", last_name="Caller", phone_number="+447700900555"),
    )
    second_target_response = client.post(
        "/auth/register",
        json=_registration_payload("match-two@example.com", "supersecure123", first_name="Casey", last_name="Caller", phone_number="+447700900555"),
    )
    assert first_target_response.status_code == 201
    assert second_target_response.status_code == 201

    second_user = db_session.exec(select(User).where(User.email == "match-two@example.com")).first()
    assert second_user is not None
    second_user.first_name = "  CASEY  "
    second_user.last_name = "  caller "
    second_user.phone_number_hash = None
    second_user.phone_number_encrypted = encrypt_sensitive_value("+44 7700 900555")
    db_session.add(second_user)
    db_session.commit()

    search_response = client.post(
        "/support/account-search",
        headers=senior_support_headers,
        json={"first_name": "Casey", "last_name": "Caller", "phone_number": "+447700900555"},
    )
    assert search_response.status_code == 200
    matches = search_response.json()
    assert len(matches) == 2
    assert {match["email"] for match in matches} == {"match-one@example.com", "match-two@example.com"}
