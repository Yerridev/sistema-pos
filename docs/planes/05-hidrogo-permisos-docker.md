# Plan de Tareas — Hidrogo Mateo Jeslyn Nicole

**Módulo:** Auth/Permisos + Paginación + Soft Delete Guard + Docker
**Rubrica:** Integración/Auth (10%) + API REST (10%) + Soft Delete (10%) + Docker (10%)

---

## Contexto Actual

El proyecto no tiene `DEFAULT_PERMISSION_CLASSES` configurado. Los endpoints de reportes `ventas-del-dia` y `stock-critico` son accesibles por cajeros (solo validan `IsAuthenticated`). No hay paginación DRF. No hay override de `delete()` en modelos para prevenir borrado físico. El `docker-compose.yml` sobreescribe el entrypoint y se salta las migraciones.

Archivos clave:
- `config/settings.py:151-156` — No hay `DEFAULT_PERMISSION_CLASSES`
- `reportes/views.py:119, 138` — `ventas_del_dia_api` y `stock_critico_api` solo usan `IsAuthenticated`
- `ventas/views.py:14` — `VentaViewSet` hereda `ModelViewSet` sin override de `destroy`
- `docker-compose.yml:18-19` — Entry point sobreescrito con `python manage.py runserver`
- `templates/login.html` — Login page

---

## Tarea 1: Agregar `DEFAULT_PERMISSION_CLASSES` en settings

En `config/settings.py`, agregar:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

Esto asegura que TODO endpoint de API requiera autenticación por defecto. Los endpoints que necesiten ser públicos deberán declarar explícitamente `permission_classes = [AllowAny]`.

---

## Tarea 2: Fix permisos en endpoints de reportes

### 2.1 Crear permisos para reportes

Crear `reportes/permissions.py`:

```python
from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """Solo usuarios con rol admin pueden acceder."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "rol", None) == "admin"
        )
```

### 2.2 Aplicar permisos a las API views de reportes

En `reportes/views.py`, cambiar:

```python
# ANTES
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ventas_del_dia_api(request):
    ...

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stock_critico_api(request):
    ...

# DESPUÉS
from reportes.permissions import IsAdminUser

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def ventas_del_dia_api(request):
    ...

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def stock_critico_api(request):
    ...
```

Nota: `utilidad_api` ya tiene un check inline (`if not _is_admin(request.user)`). Se puede mantener así o migrar a usar el permiso `IsAdminUser` para ser consistente.

---

## Tarea 3: Agregar paginación DRF

En `config/settings.py`, agregar:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

### 3.1 Verificar que los ViewSets funcionen con paginación

Los ViewSets existentes (`ProductoViewSet`, `CategoriaViewSet`, `VentaViewSet`, `CajaViewSet`, `CompraViewSet`, `ProveedorViewSet`) ya usan `get_queryset()`. La paginación se aplica automáticamente al list.

**Response esperada:**
```json
{
    "count": 150,
    "next": "http://localhost:8000/api/productos/?page=2",
    "previous": null,
    "results": [...]
}
```

### 3.2 Verificar que los templates de dashboard no se rompan

Los templates de dashboard usan `django.core.paginator.Paginator` (server-side pagination para templates), NO la paginación de DRF. Estos NO se ven afectados por el cambio en `REST_FRAMEWORK`.

Archivos que usan `Paginator` internamente:
- `ventas/dashboard_views.py:77` — `Paginator(queryset, 12)`
- `productos/views.py:146` — `Paginator(qs, 20)`

Estos siguen funcionando igual.

---

## Tarea 4: Soft Delete Guard — Override de `delete()` en modelos

### 4.1 Agregar override en `core/models.py`

Dentro de `ModeloBase` (creado por Chilcon en `core/models.py`):

```python
class ModeloBase(models.Model):
    """Modelo abstracto con campos comunes de auditoría y soft delete."""
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-creado_en']

    def delete(self, *args, **kwargs):
        """Override: soft delete en lugar de borrado físico."""
        self.activo = False
        self.save(update_fields=['activo', 'actualizado_en'])
        return 1  # Simula el retorno de QuerySet.delete()

    def eliminar(self):
        """Método explícito de soft delete."""
        self.activo = False
        self.save(update_fields=['activo', 'actualizado_en'])
```

### 4.2 Override de `delete()` en `Venta` (si hereda de ModeloBase)

Si `Venta` hereda de `ModeloBase` (tarea de Chilcon), el override se hereda automáticamente. Pero si `Venta` NO hereda de ModeloBase, se debe agregar un override manual:

```python
class Venta(models.Model):
    # ... campos existentes ...

    def delete(self, *args, **kwargs):
        """Ventas NO se eliminan físicamente."""
        raise NotImplementedError("Las ventas no se pueden eliminar físicamente. Use anular().")
```

### 4.3 Bloquear `perform_destroy` en `VentaViewSet`

En `ventas/views.py`, agregar:

```python
from rest_framework.exceptions import MethodNotAllowed

class VentaViewSet(viewsets.ModelViewSet):
    # ... código existente ...

    def destroy(self, request, *args, **kwargs):
        """Bloquear eliminación física de ventas."""
        raise MethodNotAllowed("DELETE", detail="Las ventas no se pueden eliminar. Use POST /anular/.")
```

---

## Tarea 5: Fix Docker Compose — Migrations

### 5.1 Modificar `docker-compose.yml`

```yaml
services:
  db:
    image: postgres:15
    container_name: pos_db
    restart: always
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    container_name: pos_redis
    restart: always
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  web:
    build: .
    container_name: pos_web
    entrypoint: ["./entrypoint.sh"]
    command: []
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DJANGO_DEBUG=${DJANGO_DEBUG}
      - SECRET_KEY=${SECRET_KEY}
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_HOST=db
      - DB_PORT=5432
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
  redis_data:
```

**Cambios clave:**
- `entrypoint: ["./entrypoint.sh"]` en lugar de `entrypoint: python`
- `command: []` (vacío, porque `entrypoint.sh` maneja todo)
- Agregado servicio `redis`
- Agregado `REDIS_URL` al environment de `web`
- Agregado `depends_on: redis`

### 5.2 Verificar `entrypoint.sh`

Asegurarse de que `entrypoint.sh` tenga permisos de ejecución y sea correcto:

```bash
#!/bin/bash
set -e

echo "Esperando a que PostgreSQL esté listo..."
until pg_isready -h db -p 5432 -U ${DB_USER}; do
  sleep 1
done

echo "Ejecutando migraciones..."
python manage.py migrate --noinput

echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "Iniciando servidor con Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

### 5.3 Verificar `.env.example`

Agregar `REDIS_URL` a `.env.example`:

```
SECRET_KEY=coloca-tu-clave-secreta-aqui
DJANGO_DEBUG=True
DB_NAME=pos_db
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
```

---

## Checklist de Validación

- [ ] `DEFAULT_PERMISSION_CLASSES` configurado en settings
- [ ] `reportes/permissions.py` creado con `IsAdminUser`
- [ ] `ventas_del_dia_api` y `stock_critico_api` protegidos con `IsAdminUser`
- [ ] Paginación DRF configurada (`PAGE_SIZE = 20`)
- [ ] Verificar que API responses incluyen paginación (`count`, `next`, `previous`, `results`)
- [ ] Templates de dashboard NO afectados por paginación DRF
- [ ] `ModeloBase.delete()` overridden para soft delete
- [ ] `VentaViewSet.destroy()` bloqueado con `MethodNotAllowed`
- [ ] `docker-compose.yml` corregido (entrypoint.sh, redis, migrations)
- [ ] `entrypoint.sh` tiene permisos de ejecución
- [ ] `.env.example` actualizado con `REDIS_URL`
- [ ] `docker compose up --build` ejecuta migraciones automáticamente
- [ ] Login funciona correctamente
- [ ] Cajero NO puede acceder a `/api/reportes/ventas-del-dia/` (retorna 403)
- [ ] Cajero NO puede acceder a `/api/reportes/stock-critico/` (retorna 403)

---

## Commits Convencionales Sugeridos

```
feat(config): agregar DEFAULT_PERMISSION_CLASSES y paginación DRF en settings
feat(reportes): crear IsAdminUser permission y proteger endpoints de reportes
refactor(ventas): bloquear eliminación física de ventas en VentaViewSet
fix(core): agregar override de delete() en ModeloBase para soft delete
fix(docker): corregir entrypoint y agregar servicio Redis en docker-compose
docs: actualizar .env.example con REDIS_URL
```

---

## ⚠️ CONTEXTO IMPORTANTE: Cambios de ModeloBase (commit acb3241 en develop)

> **Antes de empezar, pulled `develop` y lee esto.** Estos cambios ya están implementados y afectan directamente tu trabajo.

### Qué cambió en tus archivos clave

| Archivo | Cambio | Impacto en tu trabajo |
|---------|--------|----------------------|
| `core/models.py` | **CREADO** con `ModeloBase.delete()` override (soft delete) | **NO redefinir `delete()`** — ya está hecho. Tu trabajo es bloquear `VentaViewSet.destroy()` |
| `ventas/models.py` | `Venta` hereda `ModeloBase` | Soft delete funciona automáticamente via herencia |
| `caja/models.py` | `Caja` hereda `ModeloBase` | Soft delete funciona automáticamente |
| `compras/models.py` | `Proveedor` y `Compra` hereden `ModeloBase` | Soft delete funciona automáticamente |
| `docker-compose.yml` | `CSRF_TRUSTED_ORIGINS` agregado | Ya arreglado — vos agregás Redis y corregís entrypoint |
| `config/settings.py` | Sin cambios pendientes | Vos agregás `DEFAULT_PERMISSION_CLASSES` y `DEFAULT_PAGINATION_CLASS` |

### Soft Delete — qué ya está hecho y qué te falta

**Ya hecho (NO duplicar):**
```python
# core/models.py — ModeloBase
class ModeloBase(models.Model):
    activo = models.BooleanField(default=True)
    # ...
    
    def delete(self, *args, **kwargs):
        """Override: soft delete en lugar de borrado físico."""
        self.activo = False
        self.save(update_fields=['activo', 'actualizado_en'])
        return 1
    
    def eliminar(self):
        """Método explícito de soft delete."""
        self.activo = False
        self.save(update_fields=['activo', 'actualizado_en'])
```

**Tu trabajo (VentaViewSet.destroy):**
```python
# ventas/views.py — VentaViewSet
from rest_framework.exceptions import MethodNotAllowed

class VentaViewSet(viewsets.ModelViewSet):
    # ...
    
    def destroy(self, request, *args, **kwargs):
        """Bloquear eliminación física de ventas."""
        raise MethodNotAllowed("DELETE", detail="Las ventas no se pueden eliminar. Use POST /anular/.")
```

**Por qué:** Aunque `ModeloBase.delete()` hace soft delete, DRF llama a `perform_destroy()` que ejecuta `queryset.delete()` (QuerySet.delete, NO Model.delete). Eso SÍ borra físicamente. Por eso necesitás bloquear `destroy()` en la view.

### Permisos — qué cambió

Los campos de `Venta` y `Caja` ahora usan `creado_en` / `actualizado_en` (NO `created_at` / `updated_at`). Si en tu código de permisos o queries referenciás `created_at`, actualizalo.

### Docker Compose — estado actual

El `docker-compose.yml` actual tiene:
- Servicio `db` (PostgreSQL 15) ✅
- Servicio `web` (Django) ✅ con `CSRF_TRUSTED_ORIGINS` ✅
- **NO tiene servicio Redis** — vos lo agregás
- **Entry point sobreescrito** — vos lo corregís

### Imports que ya funcionan

```python
from core.models import ModeloBase        # Para ver la estructura
from core.exceptions import AppError      # Para excepciones
from rest_framework.exceptions import MethodNotAllowed  # Para bloquear destroy
from rest_framework.permissions import BasePermission    # Para tus permisos
```

### Cómo validar que no rompés nada

```bash
# Tests sin DB (rápido)
python manage.py test ventas caja

# Check del sistema
python manage.py check

# Verificar que el login funciona después de cambiar permisos
# Abrí http://localhost:8000/login/ y logueate
```
