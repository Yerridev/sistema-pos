# AGENTS.md

Repo-specific guidance for OpenCode sessions working on this Django POS system.
Verify against executable sources (requirements.txt, settings.py, docker-compose.yml) — the `settings.py` docstring says "Django 6.0.4" but the actual version is **5.2.13** (trust requirements.txt).

## Stack

Django 5.2.13 + DRF 3.17 + SimpleJWT + drf-spectacular. PostgreSQL 15 only (no SQLite fallback). Env via `python-decouple`. Docker Compose for db + web. Python 3.11.

## Required setup (gotchas)

- **`.env` is mandatory** — `SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` have no fallbacks. Copy `.env.example` → `.env`.
- **`DB_HOST` defaults to `db`** in `settings.py` (Docker host). For **local non-Docker dev**, set `DB_HOST=localhost` in `.env` or the app cannot reach Postgres.
- Postgres must be running for `runserver`, `migrate`, and DB-backed tests. There is no SQLite path.

## Commands

```bash
# Docker (recommended)
docker compose up -d
docker compose exec web python manage.py migrate   # migrations are NOT auto-run
docker compose exec web python manage.py createsuperuser

# Local (venv + Postgres on :5432 + .env with DB_HOST=localhost)
python manage.py migrate
python manage.py runserver

# Tests (Django Test Framework — no pytest/linter/CI configured)
python manage.py test                                       # full suite (needs Postgres)
python manage.py test ventas                                # single app
python manage.py test ventas.tests.VentasPermissionsTests   # single class
python manage.py test ventas.tests.VentasPermissionsTests.test_is_cajero_or_admin_allows_admin_and_cajero  # single method
```

Test DB gotcha: `productos/tests.py` uses DB-backed `TestCase`; `ventas/` and `caja/` use `SimpleTestCase` (no DB). DB-free unit run: `python manage.py test ventas caja`. `usuarios/`, `compras/`, `reportes` `tests.py` are empty stubs.

## Architecture

- **Project package**: `config/` (settings, urls, wsgi, asgi). `DJANGO_SETTINGS_MODULE=config.settings`.
- **Apps are top-level directories** (not nested under `apps/`): `usuarios`, `productos`, `ventas`, `caja`, `compras`, `reportes`.
- **Hybrid mode**: serves DRF JSON API **and** Django templates (login flow + dashboards). Templates live in `templates/`; dashboards are wired through `ventas/dashboard_urls.py` + `dashboard_views.py`.
- **Routing** (`config/urls.py`): a single `DefaultRouter` registers `categorias`, `productos`, `ventas`, `cajas` under `/api/`. Auth endpoints `/api/token/`, `/api/token/refresh/` use custom views in `usuarios/auth_views.py`. Swagger at `/api/docs/`, schema at `/api/schema/`. Template routes (`/login/`, `/logout/`, dashboards) are included at root.
- Not all apps expose URLs yet — `compras` and `reportes` have no `urls.py`.

## Critical model/auth facts

- **`AUTH_USER_MODEL = 'usuarios.Usuario'`** — custom user model extending `AbstractUser` with a `rol` CharField. Always use `get_user_model()` or `usuarios.Usuario` in tests/fixtures/queries; never `django.contrib.auth.models.User`.
- **Roles in the model: `admin`, `cajero` only.** The README mentions `supervisor`, but the model choices do not include it — trust the model.
- JWT login response (custom `CustomTokenObtainPairSerializer` in `usuarios/serializers.py`) includes `rol` and `user_id` alongside `access`/`refresh`. Permissions are role-gated via per-app `permissions.py` (e.g. `ventas/permissions.py`, `caja/permissions.py`).
- Locale: `LANGUAGE_CODE='es-pe'`, `TIME_ZONE='America/Lima'`, `USE_TZ=True`. UI is Spanish.

## Conventions

- **Git flow**: `main` ← `develop` ← `feature/*`. PRs target `develop`; no direct push to `main`/`develop`. Currently active branch is `develop`.
- **Conventional commits**: `feat`, `fix`, `docs`, `refactor`, `test` (scope optional, e.g. `feat(ventas): ...`). PRs reference their issue (`Closes #N`).
- Generate migrations per task, run `migrate` before opening a PR.
