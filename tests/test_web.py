def test_health_endpoint(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_home_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Wayward" in response.text
