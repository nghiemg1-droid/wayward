# Wayward

Wayward is a REST API for tracking where your electronic devices are. Each device reports its GPS position to your account, and Wayward is designed to flag a device that moves far outside its usual area as a possible theft risk.

**Status: work in progress.** Accounts, authentication and device management are done and tested. Location reporting and theft alerts are next (see the roadmap).

## Features so far

- Register and log in with email and password (passwords hashed with Argon2, never stored in plain text)
- JWT bearer tokens for authentication
- Create, list, view and delete devices, each with a home location and a radius
- Each device gets its own secret token, shown only once when it is created
- Strict ownership: a user can only see or delete their own devices (other users get a 404)
- Input validation (e.g. latitude must be between -90 and 90)
- Automated tests (pytest) running against an in-memory database

## Tech stack

Python 3.13, FastAPI, SQLAlchemy 2, SQLite, Pydantic, PyJWT, pwdlib (Argon2), pytest

## Getting started

```bash
git clone https://github.com/nghiemg1-droid/wayward.git
cd wayward
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file with a random secret key (it is git-ignored and must never be committed):

```bash
echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" > .env
```

Run the server:

```bash
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs for the interactive API documentation.

## API overview

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/auth/register` | no | Create an account |
| POST | `/auth/login` | no | Get an access token |
| GET | `/auth/me` | yes | Current user |
| POST | `/devices` | yes | Create a device (returns its token once) |
| GET | `/devices` | yes | List your devices |
| GET | `/devices/{id}` | yes | View one of your devices |
| DELETE | `/devices/{id}` | yes | Delete one of your devices |

## Running the tests

```bash
pytest -v
```

Tests use an in-memory SQLite database and their own secret key, so they never touch your real data or `.env`.

## Project structure

```
app/
  main.py        app setup and router registration
  config.py      settings loaded from environment / .env
  database.py    engine, session and Base
  models.py      User and Device tables
  schemas.py     request and response models
  auth.py        password hashing, JWT creation and current-user dependency
  routers/       users.py (auth routes) and devices.py (device routes)
tests/           pytest suite
```

## Design decisions

- **Separate response models** keep secrets out of the API: users never expose a password hash, and the device token is only returned on creation.
- **404 instead of 403** for other users' devices, so the API does not reveal whether a device exists.
- **Same error for wrong email or wrong password** on login, so accounts cannot be enumerated.
- **Tests override the database dependency** to run on a fresh in-memory database for every test.

## Roadmap

- [ ] Endpoint for devices to send location pings (authenticated with the device token)
- [ ] Distance check (haversine) against the device's home location and radius
- [ ] Theft-risk alerts with debouncing and a cooldown, delivered through a webhook
- [ ] Map dashboard showing each device's latest position
- [ ] Learn a device's usual places from its history instead of one fixed radius
- [ ] Docker, CI and a live deployment
