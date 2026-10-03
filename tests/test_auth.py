def test_register_returns_user_without_password(client):
    response = client.post(
        "/auth/register", json={"email": "a@example.com", "password": "password-123"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "a@example.com"
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email_conflicts(client):
    payload = {"email": "a@example.com", "password": "password-123"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(
        "/auth/register", json={"email": "a@example.com", "password": "short"}
    )
    assert response.status_code == 422


def test_login_with_wrong_password_fails(client, make_user):
    make_user()
    response = client.post(
        "/auth/login", data={"username": "a@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_current_user(client, make_user):
    headers = make_user()
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "a@example.com"
