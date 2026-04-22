from __future__ import annotations


def _register_admin(client) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "first_name": "Jack",
            "last_name": "Steele",
            "phone_number": "+447700900123",
            "email": "Jack.s.steele2007@icloud.com",
            "password": "StrongPass1!",
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_public_can_read_legal_documents(client):
    list_response = client.get("/content/legal")
    assert list_response.status_code == 200
    document_types = {document["document_type"] for document in list_response.json()}
    assert {"privacy", "terms", "cookies", "contact"} <= document_types

    privacy_response = client.get("/content/legal/privacy")
    assert privacy_response.status_code == 200
    assert privacy_response.json()["title"] == "Privacy Notice"

    contact_response = client.get("/content/legal/contact")
    assert contact_response.status_code == 200
    assert contact_response.json()["title"] == "Contact Details"


def test_admin_can_edit_legal_document(client):
    headers = _register_admin(client)

    update_response = client.put(
        "/content/admin/legal/privacy",
        headers=headers,
        json={
            "title": "Privacy Notice",
            "body": "Last updated: 2026-04-22\n\nUpdated admin-controlled privacy content.",
        },
    )
    assert update_response.status_code == 200
    assert "Updated admin-controlled privacy content." in update_response.json()["body"]

    public_response = client.get("/content/legal/privacy")
    assert public_response.status_code == 200
    assert "Updated admin-controlled privacy content." in public_response.json()["body"]
