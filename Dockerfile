# syntax=docker/dockerfile:1

# Images are pinned by tag and digest (of the multi-platform index, so amd64 and arm64
# builds use the same pin); Dependabot updates both.

# --- 1. Build the SPA ------------------------------------------------------------
FROM node:26-alpine@sha256:6bd9ab43c0ec0190ca7b2d193906cb8b7edf6e7f4afa43ddeccd6452710bffb5 AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
# Node 25+ no longer ships corepack: pnpm comes from npm, in the version of packageManager
# in package.json (the one place it is set).
RUN npm install -g "$(node -p "require('./package.json').packageManager.split('+')[0]")" \
 && pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm run build

# --- 2. Runtime: supervisord → nginx + gunicorn/Django -----------------------------
# Named "runtime": CI builds it without cache, so system package updates are never held back.
FROM python:3.14-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    DATA_DIR=/data

RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx gettext-base gettext \
 && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled /etc/nginx/conf.d \
 # supervisord lives outside the app's venv; it's infrastructure, not an app dependency.
 && pip install --no-cache-dir --root-user-action=ignore supervisor \
 && groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /app --no-create-home app \
 && mkdir -p /data && chown app:app /data

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
# collectstatic needs settings to import; a throwaway key is enough at build time.
# compilemessages turns the committed .po translations into .mo files.
RUN SECRET_KEY="build-only-$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')" \
    sh -c 'python manage.py collectstatic --noinput && python manage.py compilemessages --ignore=.venv'

COPY --from=frontend /frontend/dist /srv/spa
COPY docker/nginx.conf docker/django_proxy.conf docker/security_headers.conf /etc/nginx/
COPY docker/app.conf.template /etc/nginx/app.conf.template
COPY docker/supervisord.conf /etc/supervisord.conf
COPY docker/start-nginx docker/exit-on-fatal docker/healthcheck docker/smoke-test /usr/local/bin/

# Everything above is owned by root and read-only for "app"; only /data and /tmp are written.
USER app
EXPOSE 8080
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
  CMD ["python", "/usr/local/bin/healthcheck"]
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
