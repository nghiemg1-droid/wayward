# Wayward - project notes

Context for resuming work on this project in a new chat. Never put secrets, tokens or real coordinates in this file.

## Update (2026-10-04): hosting and background tracking

- Hosted on Render (free web service) with Neon (free Postgres). The fixed address is the service's onrender.com URL (not stored in this file).
- Env vars on the host: SECRET_KEY, DATABASE_URL, ACCESS_TOKEN_EXPIRE_MINUTES=1440, ALLOW_REGISTRATION (false once the owner's account exists), optional PING_RETENTION_DAYS.
- Render may not auto-deploy on push (repo access was not granted); use Manual Deploy > Deploy latest commit.
- iPhone background reporting: web pages cannot do it, so the phone runs Traccar Client, which calls GET /osmand?id=<device token>&lat=..&lon=..&accuracy=..&timestamp=.. on the server.
- Added: automatic deletion of old positions, per-email login throttling (in memory), registration switch.
- Known limits: free Render sleeps after 15 minutes idle; login throttle resets on restart; the token appears in the /osmand query string (access log disabled).
- Still to do: check background delivery on the real phone (lock screen, app swiped away), account and data deletion endpoint, privacy page, Dockerfile, "device went silent" alert, edit device (PATCH).
