import time
from datetime import datetime, timezone


def create_device(client, headers):
    payload = {"name": "Phone", "home_lat": 37.7749, "home_lng": -122.4194, "radius_m": 500}
    response = client.post("/devices", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def report(client, token, lat, lon, **extra):
    return client.get("/osmand", params={"id": token, "lat": lat, "lon": lon, **extra})


def pings_of(client, headers, device_id):
    return client.get(f"/devices/{device_id}/pings", headers=headers).json()


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def test_report_is_stored_and_updates_last_seen(client, make_user):
    headers = make_user()
    device = create_device(client, headers)

    response = report(client, device["device_token"], 37.7749, -122.4194, accuracy=8.5)

    assert response.status_code == 200
    pings = pings_of(client, headers, device["id"])
    assert len(pings) == 1
    assert pings[0]["lat"] == 37.7749
    assert pings[0]["accuracy_m"] == 8.5
    assert client.get(f"/devices/{device['id']}", headers=headers).json()["last_seen"] is not None


def test_unknown_token_is_rejected(client):
    assert report(client, "not-a-real-token", 37.7, -122.4).status_code == 401


def test_invalid_or_missing_values_are_rejected(client, make_user):
    headers = make_user()
    device = create_device(client, headers)
    token = device["device_token"]

    assert report(client, token, 95, -122.4).status_code == 422
    assert report(client, token, 37.7, -190).status_code == 422
    assert client.get("/osmand", params={"lat": 37.7, "lon": -122.4}).status_code == 422


def test_time_reported_by_the_phone_is_used(client, make_user):
    headers = make_user()
    device = create_device(client, headers)
    sent_at = int(time.time()) - 120

    report(client, device["device_token"], 37.7749, -122.4194, timestamp=sent_at)

    recorded = datetime.fromisoformat(pings_of(client, headers, device["id"])[0]["recorded_at"])
    expected = datetime.fromtimestamp(sent_at, tz=timezone.utc).replace(tzinfo=None)
    assert abs((recorded - expected).total_seconds()) < 2


def test_nonsense_times_are_ignored(client, make_user):
    headers = make_user()
    device = create_device(client, headers)
    token = device["device_token"]

    report(client, token, 37.7749, -122.4194, timestamp=int(time.time()) + 86400)
    report(client, token, 37.7749, -122.4194, timestamp="not-a-number")

    for ping in pings_of(client, headers, device["id"]):
        recorded = datetime.fromisoformat(ping["recorded_at"])
        assert abs((utc_now_naive() - recorded).total_seconds()) < 10


def test_leaving_home_through_this_route_raises_one_alert(client, make_user):
    headers = make_user()
    device = create_device(client, headers)

    for _ in range(4):
        report(client, device["device_token"], 37.8249, -122.4194)

    alerts = client.get(f"/devices/{device['id']}/alerts", headers=headers).json()
    assert len(alerts) == 1
