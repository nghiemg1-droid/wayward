def test_health_endpoint(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_home_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Wayward" in response.text


def test_report_page_is_served(client):
    response = client.get("/static/report.html")
    assert response.status_code == 200
    assert "Device token" in response.text


def test_app_manifest_and_icons_are_served(client):
    manifest = client.get("/static/manifest.json").json()
    assert manifest["name"] == "Wayward"
    assert manifest["display"] == "standalone"
    for icon in manifest["icons"]:
        response = client.get(icon["src"])
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
