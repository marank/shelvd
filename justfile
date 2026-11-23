# The project's commands — the one place they live. CI (.github/workflows/build.yaml) and the
# VS Code tasks (.vscode/tasks.json) call these recipes, so a check is changed here and
# nowhere else. `just` lists them. Needs just >= 1.38 (working-directory attribute).

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# List the recipes
default:
    @just --list

# --- Setup --------------------------------------------------------------------------

# Install all dependencies
setup: setup-backend setup-frontend

[working-directory: 'backend']
setup-backend:
    uv sync

[working-directory: 'frontend']
setup-frontend:
    pnpm install

# --- Development ----------------------------------------------------------------------

# Django on BACKEND_PORT (8000; SQLite unless DB_TYPE=postgres in .env)
[working-directory: 'backend']
dev-backend:
    uv run python manage.py runserver

# Vite on APP_PORT (8080, all interfaces), proxying /api, /admin and /media to Django
[working-directory: 'frontend']
dev-frontend:
    pnpm dev --host 0.0.0.0

# Periodic jobs of the integrations (in Docker they run on their own)
[working-directory: 'backend']
scheduler:
    uv run python manage.py run_scheduler

# Optional PostgreSQL like CI (compose.dev.yml); then DB_TYPE=postgres, DB_HOST=localhost in .env
db-up:
    docker compose -f compose.dev.yml up -d

# Apply migrations and create the first admin
[working-directory: 'backend']
migrate:
    uv run python manage.py migrate
    uv run python manage.py ensure_admin

# After model changes; commit the migrations
[working-directory: 'backend']
migrations:
    uv run python manage.py makemigrations

# After API changes: schema -> frontend/openapi.json -> src/api/schema.d.ts; commit both
[working-directory: 'frontend']
api-types: api-schema
    pnpm api:types

# Generated with SQLite like CI's check (the database decides some integer limits) and
# without add-ons: the committed schema is the published app's.
[working-directory: 'backend']
api-schema $DB_TYPE="sqlite" $ADDONS_ENABLED="false":
    uv run python manage.py export_openapi_schema --api config.api.api --indent 2 --output ../frontend/openapi.json

# After new backend texts; then translate backend/locale/de/LC_MESSAGES/django.po
[working-directory: 'backend']
messages:
    uv run python manage.py makemessages -l de --ignore=.venv --ignore=addons --no-obsolete

[working-directory: 'backend']
compile-messages:
    uv run python manage.py compilemessages --ignore=.venv

# --- Checks (= CI) --------------------------------------------------------------------

# Everything CI checks; must pass before a push
check: check-backend check-deploy check-frontend check-workflows

# Before a commit: only what the changed files can break (see scripts/check_changed.py)
check-changed:
    uv run --no-project --python ">=3.11" scripts/check_changed.py

# ruff, mypy, cognitive complexity, deptry, import layers, licenses, migrations, Django checks, translations, OpenAPI, tests
[working-directory: 'backend']
check-backend:
    uv sync --locked
    uv run ruff check --output-format=concise .
    uv run ruff format --check .
    uv run mypy .
    uv run complexipy apps config
    uv run deptry .
    uv run lint-imports
    uv run python scripts/check_licenses.py
    uv run python manage.py makemigrations --check --dry-run
    uv run python manage.py check --fail-level WARNING
    uv run python manage.py makemessages -l de --ignore=.venv --ignore=addons --no-obsolete
    uv run --with polib python scripts/check_translations.py
    uv run python manage.py compilemessages --ignore=.venv
    uv run python scripts/check_openapi.py
    uv run pytest -q --cov

# Django's deploy checks with production-like settings (deploy-check.env)
[working-directory: 'backend']
check-deploy:
    uv run --env-file deploy-check.env python manage.py check --deploy --fail-level WARNING

# prettier, oxlint, eslint, knip, types, tests, copied code, API types, build, bundle size, licenses
[working-directory: 'frontend']
check-frontend:
    pnpm install --frozen-lockfile
    pnpm check
    pnpm api:types
    git diff --exit-code -- src/api/schema.d.ts
    pnpm build-only
    pnpm size
    pnpm check:licenses

# Python, Debian, Node.js, PostgreSQL, Django: fails 180 days before their support ends.
# Not in `check`: it needs the network and its result changes with the date (weekly in CI).
[working-directory: 'backend']
check-eol:
    uv run --no-project python scripts/check_eol.py

# GitHub workflows: syntax (actionlint) and security (zizmor)
check-workflows:
    uvx --from actionlint-py==1.7.12.25 actionlint
    uvx zizmor@1.33.1 .github/

# --- Docker ----------------------------------------------------------------------------

# Build the image locally and start the production-like stack (http://localhost:8080)
docker-up $APP_IMAGE="shelvd":
    docker build -t shelvd .
    docker compose up -d

# Dump the database now (the backup service does it nightly)
docker-backup:
    docker compose exec backup sh /backup.sh now

docker-logs:
    docker compose logs -f app

docker-down:
    docker compose down
