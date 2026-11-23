# Running shelvd

How to run shelvd with Docker once the [quick start](../README.md#quick-start-with-docker) is
done. Every setting is explained in [`.env.example`](../.env.example).

## Image and updates

CI publishes `ghcr.io/marank/shelvd` for amd64 and arm64: `latest` from `main`, `sha-<commit>`
for every build and `1.2.3`, `1.2`, `1` for releases. `APP_IMAGE` in `.env` pins a version.
Each image carries a provenance attestation:

```bash
gh attestation verify oci://ghcr.io/marank/shelvd:latest --owner marank
```

Update with `docker compose pull && docker compose up -d`; the container runs Django's deploy
checks, the migrations and `ensure_admin` before it serves.

## Container

The app container runs read-only, without capabilities, as an unprivileged user; only `/data`
(covers, uploads) and `/tmp` are writable. supervisord runs gunicorn, nginx and the scheduler
(periodic jobs of the integrations, e.g. refreshing play times). `/admin` is closed unless
`ADMIN_ENABLED=true`.

Behind a TLS proxy: `APP_URLS=https://…` and `TRUSTED_PROXIES` set to the proxy's address.
Redirects from http and HSTS are the proxy's job; shelvd sets neither.

Change a password:

```bash
docker compose exec app python manage.py set_password admin
```

## First start and integrations

`ensure_admin` creates the user from `ADMIN_USERNAME` / `ADMIN_PASSWORD` (user names are
case-insensitive). External services (IGDB, HowLongToBeat, OpenCritic, TheGamesDB,
ScreenScraper) are set up by an admin in the app under **Integrations**; all are off at first.
Their keys are stored encrypted with a key derived from `SECRET_KEY` – change `SECRET_KEY` and
they have to be entered again. Without IGDB everything but the online search works; games can
then be entered by hand.

`manage.py match_metadata` matches every game against IGDB: without `--apply` only as a dry
run with a report; it takes over only what is missing or plainly wrong, never pictures
(see [data-sources.md](data-sources.md)).

## Backups

The `backup` service writes a `pg_dump` into the `backups` volume every night (`BACKUP_TIME`,
default 02:30) and keeps `BACKUP_KEEP_DAYS` days. Covers live in the `app-data` volume
(`/data/media`) and are not in the dump – back up both volumes.

```bash
docker compose exec backup sh /backup.sh now
```

```bash
docker compose cp backup:/var/lib/postgresql/backups ./backups
```

Restore (into an empty database):

```bash
docker compose exec -T backup sh -c 'pg_restore --clean --if-exists -d "$PGDATABASE"' < backups/<file>.dump
```

Dumps on the same host don't protect against losing the host – copy them away regularly.

## Source code (AGPL)

shelvd links its source on the login page, on public pages and in the user menu (AGPL § 13).
Running a modified version? Point `SOURCE_URL` in `frontend/src/lib/source.ts` at your code.
