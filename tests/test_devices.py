def create_device(client, headers, name="Laptop"):
    response = client.post(
        "/devices",
        json={"name": name, "home_lat": 37.77, "home_lng": -122.41},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_devices_require_login(client):
    assert client.get("/devices").status_code == 401
    assert client.post("/devices", json={"name": "x"}).status_code == 401


def test_create_device_returns_token_only_once(client, make_user):
    headers = make_user()
    device = create_device(client, headers)
    assert device["device_token"]

    listed = client.get("/devices", headers=headers).json()
    assert len(listed) == 1
    assert "device_token" not in listed[0]


def test_invalid_coordinates_are_rejected(client, make_user):
    headers = make_user()
    response = client.post("/devices", json={"name": "x", "home_lat": 123}, headers=headers)
    assert response.status_code == 422


def test_user_cannot_see_another_users_device(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    device = create_device(client, alice)

    assert client.get("/devices", headers=bob).json() == []
    assert client.get(f"/devices/{device['id']}", headers=bob).status_code == 404


def test_user_cannot_delete_another_users_device(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    device = create_device(client, alice)

    assert client.delete(f"/devices/{device['id']}", headers=bob).status_code == 404
    assert len(client.get("/devices", headers=alice).json()) == 1


def test_owner_can_delete_device(client, make_user):
    headers = make_user()
    device = create_device(client, headers)

    assert client.delete(f"/devices/{device['id']}", headers=headers).status_code == 204
    assert client.get(f"/devices/{device['id']}", headers=headers).status_code == 404
