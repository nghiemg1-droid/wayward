from app.config import settings


def test_registration_can_be_closed(client, monkeypatch):
    monkeypatch.setattr(settings, "allow_registration", False)
    response = client.post(
        "/auth/register", json={"email": "a@example.com", "password": "password-123"}
    )
    assert response.status_code == 403
