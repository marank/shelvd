# Developing shelvd

Conventions for everyone working on the code are in [AGENTS.md](../AGENTS.md); how changes get
in is in [CONTRIBUTING.md](../CONTRIBUTING.md).

## Stack

Django + Django Ninja (`backend/`), Vue 3 + TypeScript + Tailwind + shadcn-vue (`frontend/`),
one hardened Docker image (nginx + gunicorn + scheduler under supervisord), PostgreSQL in
production, SQLite natively.

## Requirements

- [uv](https://docs.astral.sh/uv/) (installs Python itself)
- Node.js 26 and pnpm in the version of `packageManager` in `frontend/package.json`
  (`npm install -g pnpm@<version>`)
- [just](https://just.systems/) ≥ 1.38 (`uv tool install rust-just`)
- gettext (`msgfmt`) for the backend translations
- Docker with Compose, for the image and optionally PostgreSQL

## Setup

```bash
cp .env.example .env
```

```bash
just setup && just migrate
```

`just` lists every recipe; the VS Code tasks (`.vscode/tasks.json`) call the same recipes.
**Dev: start all** (`just dev-backend` and `just dev-frontend`) runs Django on `BACKEND_PORT`
(8000) and Vite on `APP_PORT` (8080) → <http://localhost:8080>. Periodic jobs run with
`just scheduler` when needed. PostgreSQL like CI: `just db-up`, then `DB_TYPE=postgres` and
`DB_HOST=localhost` in `.env`.

Camera scanning needs a secure context: `localhost` works, a phone on the LAN only over https
(or type/scan with a USB scanner into the barcode field). Set `DEV_HTTPS=true` in `.env`: Vite
then runs with a self-signed certificate on all interfaces. Django must know the LAN address,
e.g. `APP_URLS=http://localhost:8080,https://192.168.1.20:8080`; open
`https://192.168.1.20:8080` on the phone and accept the certificate warning once.

## After changes

- Models: `just migrations`, commit the migrations.
- API: `just api-types` (schema → `frontend/openapi.json` → `src/api/schema.d.ts`), commit both.
- Backend texts: `just messages`, fill the empty `msgstr` in
  `backend/locale/de/LC_MESSAGES/django.po`, `just compile-messages`. Frontend texts live in
  `frontend/src/**/locales/{de,en}.json`.

## Checks

`just check` runs everything CI runs and must pass before a push; `just check-changed` runs only
what the changed files can break (before a commit). Backend: ruff, mypy (strict), complexipy,
deptry, import-linter, licenses, migrations, Django checks, translations, OpenAPI drift, pytest
with coverage ≥ 90 %. Frontend: prettier, oxlint, ESLint, knip, vue-tsc, Vitest with coverage,
jscpd (copied code, frontend and backend), API types drift, build, bundle budgets, licenses.
Workflows: actionlint and zizmor. Claude Code gets lint feedback after every edit
(`.claude/settings.json` → `scripts/lint_file.py`).

**Bundle budgets** (`pnpm size` after `pnpm build-only`, limits in `frontend/package.json` under
`sizeBudget`, brotli-compressed): the first start (entry script plus everything `index.html`
preloads) is kept tight, the whole app including lazily loaded pages more generous, plus CSS.
Over budget: shrink it, load it later, or raise the budget on purpose.

## CI, releases and GitHub setup

`.github/workflows/build.yaml` runs the `just` recipes, scans the repository and the image
with Trivy, builds the image natively for amd64 and arm64, smoke-tests it hardened
(`docker/smoke-test`) and pushes it to `ghcr.io/marank/shelvd`; main is rebuilt weekly, and
the weekly run also warns before Python, Debian, Node.js, PostgreSQL or Django lose support
(`just check-eol`). Dependabot proposes updates weekly. Releases come from release-please
(`.github/workflows/release.yaml`): pull request titles are Conventional Commits, the release
pull request keeps `CHANGELOG.md` and the next version; merging it tags and builds the release.

Set up once on GitHub:

1. **Ruleset for `main`:** pull requests required, squash merge only with the PR title as
   commit message, required checks `backend`, `frontend`, `workflows`, `repository`, both
   `image` jobs and (public repository) `dependency-review`.
2. **Actions → General:** "Allow GitHub Actions to create and approve pull requests" (for
   release-please). Checks on its release pull request run after "Approve and run workflows".
3. **Security:** private vulnerability reporting, Dependabot alerts, secret scanning with
   push protection, CodeQL default setup.
4. **Releases:** immutable releases on.
5. **Package:** the first push creates `ghcr.io/marank/shelvd` as private – make it public
   and link it to the repository.
