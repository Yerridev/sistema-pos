# Plan de Tareas — Puluche Espejo Pietro Ralf

**Módulo:** Service Layer + Excepciones
**Rubrica:** Service Layer + Exceptions (15%)

---

## Contexto Actual

El proyecto tiene un `core/exceptions.py` con jerarquía de excepciones muy bien diseñada. Sin embargo, dos apps NO tienen service layer (`usuarios/` y `reportes/`), y `compras/views.py` tiene lógica de negocio inline. Además, hay manejo inconsistente de excepciones en views.

Archivos clave:
- `core/exceptions.py` — Jerarquía completa: AppError → ReglaNegocioViolada → {CajaNoAbierta, ProductoSinStock, MargenInvalidoError, VentaYaAnulada}
- `usuarios/views.py` — 234 líneas, toda la lógica de CRUD directamente en views, sin service, sin excepciones del dominio
- `reportes/views.py` — Queries de datos directamente en views (funciones `ventas_del_dia_data`, `stock_critico_data`, `utilidad_data`)
- `compras/views.py:72-86` — `crear_proveedor()` con validación inline (RUC uniqueness en la view)
- `compras/serializers.py:28-33` — `CompraSerializer.create()` delega a service pero la view NO captura excepciones del dominio
- `ventas/dashboard_views.py:277-278, 327-328` — Anti-patrón `raise ValueError` dentro de `except Exception:`

---

## Tarea 1: Crear Service Layer para `usuarios/`

### 1.1 Crear `usuarios/services.py`

```python
from django.contrib.auth import get_user_model
from core.exceptions import ReglaNegocioViolada, RecursoNoEncontrado

User = get_user_model()


class UsuarioService:
    """Servicio de dominio para operaciones de usuarios."""

    @staticmethod
    def _validar_rol(rol):
        valid_roles = {value for value, _ in User.ROL_CHOICES}
        if rol not in valid_roles:
            raise ReglaNegocioViolada(f"Rol inválido. Roles válidos: {', '.join(valid_roles)}")

    @classmethod
    def crear(cls, username, password, email=None, first_name="", last_name="", rol="cajero"):
        """Crea un usuario validando unicidad de username/email y rol válido."""
        if not username.strip():
            raise ReglaNegocioViolada("El nombre de usuario es obligatorio.")
        if not password:
            raise ReglaNegocioViolada("La contraseña es obligatoria.")

        cls._validar_rol(rol)

        if User.objects.filter(username=username).exists():
            raise ReglaNegocioViolada("El nombre de usuario ya existe.")

        if email and User.objects.filter(email=email).exists():
            raise ReglaNegocioViolada("El email ya está en uso.")

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email or None,
            first_name=first_name,
            last_name=last_name,
        )
        user.rol = rol
        user.is_active = True
        user.save(update_fields=["rol", "is_active"])
        return user

    @classmethod
    def actualizar(cls, user, username, email=None, first_name="", last_name="", rol="cajero"):
        """Actualiza un usuario validando unicidad de username/email y rol válido."""
        if not username.strip():
            raise ReglaNegocioViolada("El nombre de usuario es obligatorio.")

        cls._validar_rol(rol)

        if User.objects.filter(username=username).exclude(pk=user.pk).exists():
            raise ReglaNegocioViolada("El nombre de usuario ya existe.")

        if email and User.objects.filter(email=email).exclude(pk=user.pk).exists():
            raise ReglaNegocioViolada("El email ya está en uso.")

        user.username = username
        user.email = email or ""
        user.first_name = first_name
        user.last_name = last_name
        user.rol = rol
        user.save(update_fields=["username", "email", "first_name", "last_name", "rol"])
        return user

    @staticmethod
    def toggle_activo(user, target_user):
        """Activa/desactiva un usuario. No permite desactivarse a sí mismo."""
        if target_user.pk == user.pk:
            raise ReglaNegocioViolada("No podés desactivar tu propio usuario.")
        target_user.is_active = not target_user.is_active
        target_user.save(update_fields=["is_active"])
        return target_user

    @staticmethod
    def reset_password(user, new_password):
        """Resetea la contraseña de un usuario."""
        if not new_password:
            raise ReglaNegocioViolada("La contraseña es obligatoria.")
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return user
```

### 1.2 Refactorizar `usuarios/views.py` para usar el service

Cada view debe:
1. Parsear datos del request
2. Llamar al service
3. Capturar `ReglaNegocioViolada` → retornar 400
4. Retornar respuesta con el resultado

Ejemplo para `UsuarioCreateView`:

```python
from core.exceptions import ReglaNegocioViolada

class UsuarioCreateView(View):
    def post(self, request):
        data = _parse_request_data(request)
        try:
            user = UsuarioService.crear(
                username=data.get("username", ""),
                password=data.get("password", ""),
                email=data.get("email"),
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                rol=data.get("rol", "cajero"),
            )
        except ReglaNegocioViolada as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        return JsonResponse({"success": True, "message": f'Usuario "{user.username}" creado correctamente.'}, status=201)
```

Aplicar el mismo patrón a `UsuarioUpdateView`, `UsuarioStatusView` y `UsuarioResetPasswordView`.

---

## Tarea 2: Crear Service Layer para `reportes/`

### 2.1 Crear `reportes/services.py`

Mover las funciones de datos de `reportes/views.py` a un service dedicado:

```python
from decimal import Decimal
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from productos.models import Producto
from ventas.models import DetalleVenta, Venta


class ReporteService:
    """Servicio de dominio para reportes del sistema POS."""

    @staticmethod
    def ventas_del_dia(fecha=None):
        """Retorna datos de ventas del día: total, cantidad, por método, top productos."""
        fecha = fecha or timezone.localdate()
        ventas = Venta.objects.select_related("cajero", "caja").filter(fecha__date=fecha)
        completadas = ventas.filter(estado="COMPLETADA")

        por_metodo = {
            item["metodo_pago"]: item["total"] or Decimal("0.00")
            for item in completadas.values("metodo_pago").annotate(total=Sum("total"))
        }
        top_productos = list(
            DetalleVenta.objects.filter(venta__in=completadas)
            .values(nombre=F("producto__nombre"))
            .annotate(cantidad=Sum("cantidad"), total=Sum("subtotal"))
            .order_by("-cantidad")[:5]
        )

        return {
            "fecha": fecha,
            "total": completadas.aggregate(total=Sum("total"))["total"] or Decimal("0.00"),
            "cantidad": completadas.count(),
            "por_metodo": por_metodo,
            "top_productos": top_productos,
            "ventas": ventas.order_by("-fecha"),
        }

    @staticmethod
    def stock_critico():
        """Retorna productos con stock por debajo del mínimo."""
        productos = (
            Producto.objects.select_related("categoria")
            .filter(activo=True, stock_actual__lt=F("stock_minimo"))
            .order_by("stock_actual", "nombre")
        )
        return [
            {
                "id": p.id,
                "codigo_barra": p.codigo_barra,
                "nombre": p.nombre,
                "categoria": p.categoria.nombre,
                "stock_actual": p.stock_actual,
                "stock_minimo": p.stock_minimo,
                "sugerencia_reposicion": max((p.stock_minimo * 2) - p.stock_actual, 0),
            }
            for p in productos
        ]

    @staticmethod
    def utilidad(desde=None, hasta=None):
        """Retorna utilidad (ingresos vs costos) por período."""
        ventas = Venta.objects.filter(estado="COMPLETADA")
        if desde:
            ventas = ventas.filter(fecha__date__gte=desde)
        if hasta:
            ventas = ventas.filter(fecha__date__lte=hasta)

        detalles = DetalleVenta.objects.filter(venta__in=ventas).select_related("producto", "venta")
        ingresos = ventas.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        costo = sum(detalle.producto.costo * detalle.cantidad for detalle in detalles)
        utilidad = ingresos - costo
        por_dia = list(
            ventas.annotate(dia=TruncDate("fecha"))
            .values("dia")
            .annotate(total=Sum("total"), ventas=Count("id"))
            .order_by("dia")
        )
        return {
            "desde": desde,
            "hasta": hasta,
            "ingresos": ingresos,
            "costos": costo,
            "utilidad": utilidad,
            "por_dia": por_dia,
        }
```

### 2.2 Refactorizar `reportes/views.py` para usar el service

```python
from reportes.services import ReporteService

def reportes_dashboard(request):
    fecha = _parse_date(request, "fecha", timezone.localdate())
    desde = _parse_date(request, "desde")
    hasta = _parse_date(request, "hasta")
    return render(request, "dashboard/reportes.html", {
        "ventas_dia": ReporteService.ventas_del_dia(fecha),
        "stock_critico": ReporteService.stock_critico(),
        "utilidad": ReporteService.utilidad(desde, hasta),
        "filters": {"fecha": fecha, "desde": desde, "hasta": hasta},
        "page_title": "Reportes",
        "active_nav": "reportes:dashboard",
    })
```

Mismo patrón para las API views (`ventas_del_dia_api`, `stock_critico_api`, `utilidad_api`).

---

## Tarea 3: Fix manejo de excepciones en `compras/`

### 3.1 Agregar error handling en `CompraViewSet`

En `compras/views.py`, el `CompraViewSet` actual NO captura excepciones del dominio:

```python
# ACTUAL (compras/views.py:24-31) — SIN manejo de errores
class CompraViewSet(viewsets.ModelViewSet):
    queryset = Compra.objects.select_related("proveedor").prefetch_related("detalles__producto")
    serializer_class = CompraSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
```

Cambiar a:

```python
from rest_framework import status
from rest_framework.response import Response
from core.exceptions import AppError, ReglaNegocioViolada, RecursoNoEncontrado

class CompraViewSet(viewsets.ModelViewSet):
    queryset = Compra.objects.select_related("proveedor").prefetch_related("detalles__producto")
    serializer_class = CompraSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            compra = serializer.save()
        except ReglaNegocioViolada as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RecursoNoEncontrado as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except AppError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(compra).data, status=status.HTTP_201_CREATED)
```

### 3.2 Crear `compras/services.py` para `crear_proveedor()`

Mover la lógica de `crear_proveedor()` (que está inline en `compras/views.py:72-86`) a un service:

```python
# compras/services.py
from core.exceptions import ReglaNegocioViolada
from .models import Proveedor


class ProveedorService:
    @classmethod
    def crear(cls, nombre, ruc, contacto=""):
        if not nombre.strip():
            raise ReglaNegocioViolada("El nombre del proveedor es obligatorio.")
        if not ruc or len(ruc) != 11:
            raise ReglaNegocioViolada("El RUC debe tener 11 dígitos.")
        if Proveedor.objects.filter(ruc=ruc).exists():
            raise ReglaNegocioViolada("Ya existe un proveedor con ese RUC.")
        return Proveedor.objects.create(
            nombre=nombre.strip(),
            ruc=ruc,
            contacto=contacto,
        )
```

Y refactorizar `compras/views.py` para usar el service.

---

## Tarea 4: Fix anti-patrón en `ventas/dashboard_views.py`

En `ventas/dashboard_views.py` hay un patrón defectuoso en líneas 277-278 y 327-328:

```python
# ANTI-PATRÓN ACTUAL
except Exception:
    raise ValueError  # ← Se lanza y se atrapa inmediatamente
```

Cambiar a un manejo limpio:

```python
# CORRECTO
except (ValueError, TypeError, InvalidOperation):
    return JsonResponse({"error": "Datos numéricos inválidos."}, status=400)
```

Revisar las funciones `abrir_caja`, `cerrar_caja` y `registrar_movimiento_caja` en ese archivo.

---

## Checklist de Validación

- [ ] `usuarios/services.py` creado con `UsuarioService`
- [ ] `usuarios/views.py` refactorizado para usar `UsuarioService`
- [ ] `usuarios/views.py` captura `ReglaNegocioViolada` → 400
- [ ] `reportes/services.py` creado con `ReporteService`
- [ ] `reportes/views.py` refactorizado para usar `ReporteService`
- [ ] `compras/views.py` — `CompraViewSet.create()` maneja excepciones del dominio
- [ ] `compras/services.py` creado con `ProveedorService`
- [ ] `compras/views.py` — `crear_proveedor()` refactorizado para usar service
- [ ] Anti-patrón `raise ValueError` en `dashboard_views.py` eliminado
- [ ] Todos los tests existentes pasan
- [ ] No hay lógica de negocio directamente en views

---

## Commits Convencionales Sugeridos

```
feat(usuarios): crear UsuarioService con CRUD validado
refactor(usuarios): migrar views a usar UsuarioService
feat(reportes): crear ReporteService con datos de reportes
refactor(reportes): migrar views a usar ReporteService
fix(compras): agregar error handling en CompraViewSet
feat(compras): crear ProveedorService para creación de proveedores
fix(ventas): eliminar anti-patrón raise ValueError en dashboard_views
```

---

## ⚠️ CONTEXTO IMPORTANTE: Cambios de ModeloBase (commit acb3241 en develop)

> **Antes de empezar, pulled `develop` y lee esto.** Estos cambios ya están implementados y afectan directamente tu trabajo.

### Qué cambió en tus archivos clave

| Archivo | Cambio | Impacto en tu trabajo |
|---------|--------|----------------------|
| `core/models.py` | CREADO con `ModeloBase` y `ManagerActivos` | Tus services pueden importar de `core` — NO hay riesgo de import circular |
| `core/exceptions.py` | Sin cambios | Tus excepciones (`ReglaNegocioViolada`, `RecursoNoEncontrado`, etc.) siguen igual |
| `usuarios/views.py` | Sin cambios de ModeloBase | Tu trabajo principal: crear `usuarios/services.py` y refactorizar estas views |
| `reportes/views.py` | Sin cambios de ModeloBase | Tu trabajo: crear `reportes/services.py` y refactorizar estas views |
| `compras/views.py` | Sin cambios de ModeloBase | Tu trabajo: crear `compras/services.py` y fix error handling |
| `ventas/dashboard_views.py` | Sin cambios de ModeloBase | Tu trabajo: fix anti-patrón `raise ValueError` en líneas 277-278 y 327-328 |

### Cómo crear tus services (patrón a seguir)

El patrón ya existe en `productos/services.py` y `ventas/services.py`. Seguí la misma estructura:

```python
# Ejemplo: usuarios/services.py
from django.contrib.auth import get_user_model
from core.exceptions import ReglaNegocioViolada

User = get_user_model()

class UsuarioService:
    @classmethod
    def crear(cls, username, password, ...):
        # 1. Validar datos de entrada
        # 2. Verificar unicidad
        # 3. Crear objeto
        # 4. Retornar objeto creado
```

### Dónde están los anti-patrones que debés corregir

En `ventas/dashboard_views.py`, buscá estos patrones y reemplazalos:

```python
# ANTI-PATRÓN (líneas ~277-278, ~327-328)
except Exception:
    raise ValueError

# CORRECTO
except (ValueError, TypeError, InvalidOperation):
    return JsonResponse({"error": "Datos numéricos inválidos."}, status=400)
```

### Imports que ya funcionan

- `from core.exceptions import ReglaNegocioViolada, RecursoNoEncontrado, AppError` → funciona
- `from django.contrib.auth import get_user_model` → funciona
- `from productos.models import Producto` → funciona
- `from ventas.models import Venta, DetalleVenta` → funciona
- `from caja.models import Caja, MovimientoCaja` → funciona
- `from compras.models import Compra, Proveedor` → funciona

### Cómo validar que no rompés nada

```bash
# Tests sin DB (rápido)
python manage.py test ventas caja

# Tests con DB (necesita Docker)
python manage.py test

# Check del sistema
python manage.py check
```
