# Wayward

[![Tests](https://github.com/nghiemg1-droid/wayward/actions/workflows/ci.yml/badge.svg)](https://github.com/nghiemg1-droid/wayward/actions/workflows/ci.yml)

Wayward is a REST API for tracking where your electronic devices are. Each device reports its GPS position to your account. When a device stays outside its home area for several consecutive readings, Wayward records an alert and notifies you through a webhook.

**Status: work in progress.** The core loop works end to end: accounts, devices, location reporting, alert detection and notification. A dashboard and smarter "usual place" detection are next (see the roadmap).

## Features

- Register and log in with email and password (passwords hashed with Argon2, never stored in plain text)
- JWT bearer tokens for authentication
- Create, list, view and delete devices, each with a home location and a radius
- Each device gets its own secret token, shown only once, which it uses to report positions (`X-Device-Token` header)
- Location pings are stored with accuracy and timestamp; every ping updates the device's `last_seen`
- Theft-risk alerts when a device stays away from home (see below), stored and listed per device
- Optional webhook notification (Discord-style `{"content": ...}` payload); without a webhook the alert is written to the server log
- Strict ownership: a user can only see or delete their own devices, pings and alerts (other users get a 404)
- Input validation (e.g. latitude must be between -90 and 90)
- A device simulator script for trying the whole flow
- Automated tests (pytest) running against an in-memory database

## How alerts work

The decision lives in one pure function, `should_alert`, in `app/services/alert_rules.py`, which is unit-tested on its own:

1. Readings with poor GPS accuracy (worse than 100 m) are ignored.
2. An alert only fires when the 3 most recent accurate readings are all outside the device's radius, so a single GPS glitch does not trigger it.
3. After an alert, no new alert is created for 30 minutes (cooldown).

When a ping arrives, the server stores it, asks `should_alert`, saves an `Alert` if needed, and sends the notification in a background task so the device gets a fast response.

## Tech stack

Python 3.13, FastAPI, SQLAlchemy 2, SQLite, Pydantic, PyJWT, pwdlib (Argon2), httpx, pytest

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

### Configuration

Settings are read from environment variables or `.env`:

| Variable | Required | Description |
| --- | --- | --- |
| `SECRET_KEY` | yes | Key used to sign JWT tokens |
| `DATABASE_URL` | no | Defaults to a local SQLite file |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | Defaults to 60 |
| `ALERT_WEBHOOK_URL` | no | Where to send alert messages; if empty, alerts are logged |

## Try it with the simulator

1. In `/docs`, register an account, log in with **Authorize**, and create a device with a home location, for example `{"name": "Test phone", "home_lat": 37.7749, "home_lng": -122.4194, "radius_m": 500}`. Copy the `device_token` from the response.
2. In another terminal run the simulator, which sends 3 positions near home and then jumps about 5 km away:

```bash
python scripts/simulate_device.py --count 8 --jump-after 3
```

3. Paste the token when asked. After the third consecutive position away from home, the server logs an `ALERT` line (or posts to your webhook), and `GET /devices/{id}/alerts` lists it.

## API overview

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/auth/register` | no | Create an account |
| POST | `/auth/login` | no | Get an access token |
| GET | `/auth/me` | user | Current user |
| POST | `/devices` | user | Create a device (returns its token once) |
| GET | `/devices` | user | List your devices |
| GET | `/devices/{id}` | user | View one of your devices |
| DELETE | `/devices/{id}` | user | Delete one of your devices |
| POST | `/pings` | device token | Report a position |
| GET | `/devices/{id}/pings` | user | Recent positions, newest first |
| GET | `/devices/{id}/alerts` | user | Alerts for one of your devices |

## Running the tests

```bash
pytest -v
```

Tests use an in-memory SQLite database, their own secret key and no webhook, so they never touch your real data or `.env`.

## Project structure

```
app/
  main.py        app setup and router registration
  config.py      settings loaded from environment / .env
  database.py    engine, session and Base
  models.py      User, Device, Ping and Alert tables
  schemas.py     request and response models
  auth.py        password hashing, JWT creation and current-user dependency
  routers/       users.py, devices.py and pings.py (pings and alerts)
  services/      geo.py (haversine distance), alert_rules.py (pure alert decision),
                 alerting.py (stores alerts), notifier.py (webhook)
scripts/         simulate_device.py
tests/           pytest suite
```

## Design decisions

- **Separate response models** keep secrets out of the API: users never expose a password hash, and the device token is only returned on creation.
- **Two kinds of authentication**: users log in with a JWT, devices report with their own token, so a leaked device token cannot be used to log in to an account.
- **404 instead of 403** for other users' devices, so the API does not reveal whether a device exists.
- **Same error for wrong email or wrong password** on login, so accounts cannot be enumerated.
- **A pure alert function** keeps the decision logic free of database and network code, which makes it easy to test thoroughly.
- **Notifications run in the background**, and webhook failures are logged instead of breaking the ping request.
- **Tests override the database dependency** to run on a fresh in-memory database for every test.

## Roadmap

- [x] Accounts, JWT authentication and device management
- [x] Endpoint for devices to send location pings (authenticated with the device token)
- [x] Distance check (haversine) against the device's home location and radius
- [x] Theft-risk alerts with debouncing and a cooldown, delivered through a webhook
- [x] Device simulator script
- [x] Continuous integration (run the tests on every push)
- [ ] Map dashboard showing each device's latest position
- [ ] Learn a device's usual places from its history instead of one fixed radius
- [ ] "Device went silent" alert
- [ ] Docker and a live deployment
