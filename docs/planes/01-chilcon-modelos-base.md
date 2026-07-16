# Plan de Tareas — Chilcon Ramirez Abondanyerri

**Módulo:** Modelos y Base de Datos
**Rubrica:** ModeloBase (10%) + CheckConstraints (parte de Modelos 10%)

---

## Contexto Actual

El proyecto NO tiene un `ModeloBase` abstracto. Cada modelo define `activo`, `created_at`, `updated_at` de forma independiente (o no los tiene). No existe `ManagerActivos`. No hay `CheckConstraint` a nivel de BD para `stock >= 0` ni `precio_venta >= costo`.

Archivos clave:
- `productos/models.py` — Modelo con campos manuales (activo, created_at, updated_at)
- `core/` — Solo tiene `exceptions.py`, no hay `models.py`
- Ningún modelo hereda de una base abstracta

---

## Tarea 1: Crear `ModeloBase` (core/models.py)

**Crear** `core/models.py` con:

```python
from django.db import models


class ModeloBase(models.Model):
    """Modelo abstracto con campos comunes de auditoría y soft delete."""
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-creado_en']

    def eliminar(self):
        """Soft delete: desactiva el registro sin borrarlo."""
        self.activo = False
        self.save(update_fields=['activo', 'actualizado_en'])
```

**Archivos a crear:**
- `core/__init__.py` (si no existe, ya existe)
- `core/models.py`

**Nota:** Los campos se llaman `creado_en` / `actualizado_en` (no `created_at` / `updated_at`) para seguir el estándar en español de la rúbrica. Si el equipo prefiere mantener `created_at`/`updated_at` por consistencia con lo que ya existe en `productos/models.py`, avisar antes de implementar.

---

## Tarea 2: Crear `ManagerActivos`

Dentro de `core/models.py`, agregar:

```python
class ManagerActivos(models.Manager):
    """Manager que retorna solo registros activos."""
    def get_queryset(self):
        return super().get_queryset().filter(activo=True)
```

Cada modelo que herede de `ModeloBase` deberá tener:

```python
class MiModelo(ModeloBase):
    objects = ManagerActivos()
    all_objects = models.Manager()  # Para acceder a todos (incluidos inactivos)

    class Meta(ModeloBase.Meta):
        pass
```

---

## Tarea 3: Migrar modelos existentes a heredar de `ModeloBase`

Modelos a migrar (agregar herencia + `ManagerActivos` + `all_objects`):

| Modelo | Archivo | Cambio |
|--------|---------|--------|
| `Categoria` | `productos/models.py:5` | Hereda `ModeloBase`, elimina `activo`, `created_at`, `updated_at` manuales |
| `Producto` | `productos/models.py:21` | Hereda `ModeloBase`, elimina `activo`, `created_at`, `updated_at` manuales |
| `Proveedor` | `compras/models.py:7` | Hereda `ModeloBase`, elimina `activo` manual (no tiene timestamps) |
| `Venta` | `ventas/models.py:17` | **AGREGAR** herencia `ModeloBase` (actualmente no tiene `activo` ni timestamps) |
| `DetalleVenta` | `ventas/models.py:66` | **NO migrar** — es una línea de detalle, no necesita soft delete |
| `Caja` | `caja/models.py:6` | **AGREGAR** herencia `ModeloBase` (actualmente no tiene `activo` ni timestamps) |
| `MovimientoCaja` | `caja/models.py:38` | **NO migrar** — es un registro de movimiento, no necesita soft delete |
| `Compra` | `compras/models.py:21` | **AGREGAR** herencia `ModeloBase` |
| `DetalleCompra` | `compras/models.py:44` | **NO migrar** — es línea de detalle |
| `Usuario` | `usuarios/models.py:5` | **NO migrar** — ya hereda de `AbstractUser` que tiene `is_active` y `date_joined` |

**Importante:** Al migrar, se deben conservar los `related_name` existentes en los ForeignKey. Ejemplo: `Venta` tiene `ForeignKey` a `Caja` con `related_name='ventas'` — este no puede cambiar.

---

## Tarea 4: Agregar `CheckConstraint` a nivel de BD

En `productos/models.py`, dentro de `class Meta` de `Producto`:

```python
class Meta:
    ordering = ['nombre']
    indexes = [
        models.Index(fields=['codigo_barra']),
        models.Index(fields=['categoria']),
        models.Index(fields=['activo']),
    ]
    constraints = [
        models.CheckConstraint(
            check=models.Q(stock_actual__gte=0),
            name='stock_no_negativo',
        ),
        models.CheckConstraint(
            check=models.Q(precio_venta__gte=models.F('costo')),
            name='precio_venta_mayor_igual_costo',
        ),
    ]
```

**Nota sobre `precio_venta >= costo`:** El serializer (`productos/serializers.py:32-39`) Y el service (`productos/services.py:11-13`) ya validan esto a nivel de aplicación. El `CheckConstraint` agrega protección a nivel de BD para que un SQL raw no pueda violar la regla.

**Generar migración después de los cambios:**
```bash
python manage.py makemigrations productos caja ventas compras
python manage.py migrate
```

---

## Tarea 5: Actualizar Services para usar `all_objects` donde corresponda

Revisar los services que actualmente filtran `activo=True` manualmente y cambiarlos para usar `all_objects` cuando necesiten acceder a inactivos:

- `productos/services.py:94-98` — `ProductoService.eliminar()` usa `producto.activo = False`. Esto sigue funcionando con `ModeloBase`.
- `ventas/services.py` — `VentaService` consulta `Venta`. Si `Venta` hereda `ModeloBase`, el `objects` manager filtrará por `activo=True`. Verificar que las queries de venta no rompan.

**Verificar:** Después de migrar, correr:
```bash
python manage.py test productos
python manage.py test ventas
python manage.py test caja
python manage.py test compras
```

---

## Checklist de Validación

- [ ] `core/models.py` creado con `ModeloBase` y `ManagerActivos`
- [ ] `Categoria` y `Producto` heredan de `ModeloBase` (eliminados campos manuales)
- [ ] `Proveedor` hereda de `ModeloBase`
- [ ] `Venta`, `Caja`, `Compra` heredan de `ModeloBase` (nuevos campos `activo`, timestamps)
- [ ] `DetalleVenta`, `MovimientoCaja`, `DetalleCompra`, `Usuario` NO migrados
- [ ] `CheckConstraint` `stock_no_negativo` agregado
- [ ] `CheckConstraint` `precio_venta_mayor_igual_costo` agregado
- [ ] Migraciones generadas y aplicadas
- [ ] Todos los tests existentes pasan
- [ ] No hay errores de import circular entre `core` y las apps

---

## Commits Convencionales Sugeridos

```
feat(core): crear ModeloBase y ManagerActivos en core/models.py
refactor(productos): migrar Categoria y Producto a heredar de ModeloBase
refactor(compras): migrar Proveedor y Compra a heredar de ModeloBase
refactor(ventas): migrar Venta a heredar de ModeloBase
refactor(caja): migrar Caja a heredar de ModeloBase
feat(productos): agregar CheckConstraint stock_negativo y precio_venta_vs_costo
```

---

## ✅ CAMBIOS IMPLEMENTADOS (commit acb3241 en develop)

> **Este plan YA fue implementado.** No volver a ejecutar. Los archivos ya están en `develop`.

### Archivos creados/modificados

| Archivo | Estado | Qué tiene |
|---------|--------|-----------|
| `core/models.py` | CREADO | `ModeloBase` (abstract) + `ManagerActivos` + `all_objects` + `eliminar()` + `delete()` override (soft delete) |
| `productos/models.py` | MODIFICADO | `Categoria` y `Producto` heredan `ModeloBase`. CheckConstraints: `stock_no_negativo`, `precio_venta_mayor_igual_costo` |
| `compras/models.py` | MODIFICADO | `Proveedor` y `Compra` heredan `ModeloBase` |
| `ventas/models.py` | MODIFICADO | `Venta` hereda `ModeloBase` |
| `caja/models.py` | MODIFICADO | `Caja` hereda `ModeloBase` |
| `productos/admin.py` | MODIFICADO | `created_at` → `creado_en`, `updated_at` → `actualizado_en` |
| `productos/serializers.py` | MODIFICADO | Mismo rename de campos |
| `productos/services.py` | MODIFICADO | Mismo rename de campos |
| `productos/views.py` | MODIFICADO | Mismo rename de campos |
| `docker-compose.yml` | MODIFICADO | `CSRF_TRUSTED_ORIGINS` agregado |
| Migraciones `0002_modelobase_transition.py` | CREADAS | En productos, compras, ventas, caja — renombran/agregan columnas preservando datos |

### Cosas que los demás integrantes DEBEN saber

1. **`Venta` hereda `ModeloBase`** → tiene `activo=True` por defecto, `creado_en`, `actualizado_en`
2. **`Caja` hereda `ModeloBase`** → idem
3. **`Proveedor` y `Compra` heredan `ModeloBase`** → idem
4. **`ModeloBase` tiene `delete()` override** → hace soft delete (setea `activo=False`). Hidrogo NO necesita redefinirlo.
5. **`objects` manager ya filtra por `activo=True`** → queries normales solo ven registros activos. Para ver inactivos: `Modelo.all_objects.filter(...)`
6. **Campos se llaman `creado_en` / `actualizado_en`** (NO `created_at` / `updated_at`)
7. **Migraciones de transición ya aplicadas** → la DB tiene los campos nuevos con valores por defecto (`activo=True`, timestamps auto)
