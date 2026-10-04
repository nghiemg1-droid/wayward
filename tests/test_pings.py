def create_device(client, headers):
    response = client.post("/devices", json={"name": "Phone"}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def send_ping(client, token, lat=37.77, lng=-122.41):
    return client.post(
        "/pings", json={"lat": lat, "lng": lng}, headers={"X-Device-Token": token}
    )


def test_ping_requires_a_valid_device_token(client):
    assert client.post("/pings", json={"lat": 1, "lng": 1}).status_code == 422
    assert send_ping(client, "not-a-real-token").status_code == 401


def test_ping_is_stored_and_updates_last_seen(client, make_user):
    headers = make_user()
    device = create_device(client, headers)
    assert device["last_seen"] is None

    response = send_ping(client, device["device_token"])
    assert response.status_code == 201
    assert response.json()["lat"] == 37.77

    updated = client.get(f"/devices/{device['id']}", headers=headers).json()
    assert updated["last_seen"] is not None


def test_invalid_coordinates_are_rejected(client, make_user):
    headers = make_user()
    device = create_device(client, headers)
    assert send_ping(client, device["device_token"], lat=95).status_code == 422
    assert send_ping(client, device["device_token"], lng=-181).status_code == 422


def test_owner_can_list_pings_newest_first(client, make_user):
    headers = make_user()
    device = create_device(client, headers)
    send_ping(client, device["device_token"], lat=10)
    send_ping(client, device["device_token"], lat=20)

    pings = client.get(f"/devices/{device['id']}/pings", headers=headers).json()
    assert [p["lat"] for p in pings] == [20, 10]


def test_user_cannot_list_another_users_pings(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    device = create_device(client, alice)
    send_ping(client, device["device_token"])

    assert client.get(f"/devices/{device['id']}/pings", headers=bob).status_code == 404


def test_deleting_a_device_invalidates_its_token(client, make_user):
    headers = make_user()
    device = create_device(client, headers)
    assert send_ping(client, device["device_token"]).status_code == 201

    assert client.delete(f"/devices/{device['id']}", headers=headers).status_code == 204
    assert send_ping(client, device["device_token"]).status_code == 401
