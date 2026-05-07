# AGENTS.md — sistema-pos

## Resumen del Proyecto

Sistema POS (Punto de Venta) para comercios retail peruanos. Etapa: **Auth + Login frontend implementados**. Lógica de negocio (productos, ventas, caja, compras, reportes) pendiente.

**Stack:** Django 5.2, DRF 3.17, SimpleJWT, drf-spectacular (OpenAPI), PostgreSQL 15, Docker Compose.
**Localización:** `es-pe`, zona horaria `America/Lima`, moneda PEN (S/.)

## Estado de Implementación

| App | Estado | Detalle |
|-----|--------|---------|
| `usuarios/` | ✅ Listo | Modelo Usuario con roles, auth JWT endpoint, login template |
| `productos/` | 🔲 Pendiente | CRUD completo |
| `ventas/` | 🔲 Pendiente | POS logic |
| `caja/` | 🔲 Pendiente | Apertura/cierre |
| `compras/` | 🔲 Pendiente | Proveedores |
| `reportes/` | 🔲 Pendiente | Reportes |

## Comandos Esenciales

```bash
# === Docker Compose (RECOMENDADO) ===
docker compose up -d              # Levanta web + db
docker compose down               # Detiene
docker compose up -d db           # Solo db
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose logs -f web        # Ver logs

# === Desarrollo Local ===
python -m venv venv
venv\Scripts\activate             # Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py makemigrations   # después de cambios en modelos
python manage.py createsuperuser
python manage.py runserver
python manage.py check
python manage.py showmigrations
```

**No hay linter, formatter ni test runner configurados aún.**

## Arquitectura

```
config/           ← Settings de Django, urls, wsgi/asgi
templates/        ← Plantillas HTML (login.html)
usuarios/         ← Modelo Usuario + Auth API [IMPLEMENTADO]
│   ├── auth_views.py    ← CustomTokenObtainPairView, CustomTokenRefreshView
│   ├── serializers.py   ← CustomTokenObtainPairSerializer (rol en response)
│   └── views.py         ← login_view (renderiza login.html)
productos/        ← [PENDIENTE]
ventas/           ← [PENDIENTE]
caja/             ← [PENDIENTE]
compras/          ← [PENDIENTE]
reportes/         ← [PENDIENTE]
```

## Endpoints Implementados

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/token/` | Login — retorna `access`, `refresh`, `rol`, `user_id` |
| POST | `/api/token/refresh/` | Renovar access token |
| GET | `/login/` | Página de login (Tailwind/CSS) |
| GET | `/api/docs/` | Swagger UI |
| GET | `/api/schema/` | OpenAPI JSON |

## Gotchas de Configuración

- **`.env` es obligatorio** — `SECRET_KEY`, `DB_*`, `DEBUG` cargados con `python-decouple`.
- **Solo PostgreSQL** — no hay fallback a SQLite.
- **`DB_HOST=db`** en `.env` para Docker; `DB_HOST=localhost` para desarrollo local.
- **`AUTH_USER_MODEL = 'usuarios.Usuario'`** — nunca usar `django.contrib.auth.models.User`.
- **`ALLOWED_HOSTS = ['*']`** — solo desarrollo.
- **JWT único** — session auth desactivado, solo Bearer tokens.

## Sistema de Roles

El modelo `Usuario` tiene campo `rol` con choices:
- `admin` — acceso total
- `cajero` — ventas y caja
- `supervisor` — acceso mixto

**Estado actual:** El `rol` viene en el response del login pero **no hay restrictions de permisos implementadas** en las vistas. Esto es pendiente para el feature de productos.

## Flujo de Trabajo Git

- **Ramas:** `main` ← `develop` ← `feature/nombre`
- **PRs:** apuntar a `develop`
- **Commits:** convencionales — `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- **Remoto:** `https://github.com/Yerridev/sistema-pos`

## Notas de Desarrollo

- **Proyecto universitario** de 5 estudiantes (Grupo 6, USS Chiclayo).
- Requiere **facturación electrónica SUNAT** (XML UBL 2.1, integración PSE/OSE).
- Al agregar nuevas apps: registrar en `INSTALLED_APPS` y conectar URLs en `config/urls.py`.
- **Sin tests aún** — Django Test Framework disponible, pytest-django pendiente.
- **Dualidad frontend:** El backend puede servir tanto templates Django como API JSON (modo híbrido).
