HOME = {"home_lat": 37.7749, "home_lng": -122.4194, "radius_m": 500}
AT_HOME = 37.7749
FAR_AWAY = 37.8249  # about 5.5 km north of home


def create_device(client, headers, **extra):
    response = client.post("/devices", json={"name": "Phone", **HOME, **extra}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def send_ping(client, token, lat, accuracy_m=10):
    response = client.post(
        "/pings",
        json={"lat": lat, "lng": -122.4194, "accuracy_m": accuracy_m},
        headers={"X-Device-Token": token},
    )
    assert response.status_code == 201, response.text


def alerts_of(client, headers, device_id):
    return client.get(f"/devices/{device_id}/alerts", headers=headers).json()


def test_leaving_home_creates_exactly_one_alert(client, make_user):
    headers = make_user()
    device = create_device(client, headers)
    token = device["device_token"]

    for _ in range(3):
        send_ping(client, token, AT_HOME)
    assert alerts_of(client, headers, device["id"]) == []

    for _ in range(6):
        send_ping(client, token, FAR_AWAY)

    alerts = alerts_of(client, headers, device["id"])
    assert len(alerts) == 1  # the cooldown stops repeat alerts
    assert alerts[0]["distance_m"] > 5000


def test_a_single_gps_glitch_does_not_create_an_alert(client, make_user):
    headers = make_user()
    device = create_device(client, headers)
    token = device["device_token"]

    for lat in [AT_HOME, AT_HOME, FAR_AWAY, AT_HOME, AT_HOME]:
        send_ping(client, token, lat)

    assert alerts_of(client, headers, device["id"]) == []


def test_device_without_home_location_never_alerts(client, make_user):
    headers = make_user()
    response = client.post("/devices", json={"name": "No home"}, headers=headers)
    device = response.json()

    for _ in range(5):
        send_ping(client, device["device_token"], FAR_AWAY)

    assert alerts_of(client, headers, device["id"]) == []


def test_user_cannot_see_another_users_alerts(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    device = create_device(client, alice)

    response = client.get(f"/devices/{device['id']}/alerts", headers=bob)
    assert response.status_code == 404


def test_alert_message_is_sent_to_the_notifier(client, make_user, monkeypatch):
    sent = []
    monkeypatch.setattr("app.routers.pings.send_alert_message", sent.append)
    headers = make_user()
    device = create_device(client, headers)

    for _ in range(3):
        send_ping(client, device["device_token"], FAR_AWAY)

    assert len(sent) == 1
    assert "Phone" in sent[0]
