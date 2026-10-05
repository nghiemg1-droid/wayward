import pytest

from app.services import login_limiter


@pytest.fixture(autouse=True)
def clean_limiter():
    login_limiter.clear_all()
    yield
    login_limiter.clear_all()


def login(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password})


def test_repeated_failures_block_even_the_right_password(client, make_user):
    make_user()
    for _ in range(5):
        assert login(client, "a@example.com", "wrong-password").status_code == 401

    response = login(client, "a@example.com", "password-123")
    assert response.status_code == 429
    assert "retry-after" in response.headers


def test_other_accounts_are_not_blocked(client, make_user):
    make_user("a@example.com")
    make_user("b@example.com")
    for _ in range(5):
        login(client, "a@example.com", "wrong-password")

    assert login(client, "b@example.com", "password-123").status_code == 200


def test_a_successful_login_resets_the_counter(client, make_user):
    make_user()
    for _ in range(4):
        login(client, "a@example.com", "wrong-password")
    assert login(client, "a@example.com", "password-123").status_code == 200

    for _ in range(4):
        login(client, "a@example.com", "wrong-password")
    assert login(client, "a@example.com", "password-123").status_code == 200
