# Plan de Tareas — Chinchay Campos Jhon Jairo

**Módulo:** Nivel 2 — Strategy Pattern + Redis Cache
**Rubrica:** Nivel 2 (15%)

---

## Contexto Actual

El sistema NO tiene implementado Strategy Pattern para políticas de descuento, ni Redis Cache para búsqueda de productos. La búsqueda de productos por código de barras va directo a PostgreSQL cada vez. Los descuentos son un valor escalar simple en el modelo `Venta`.

Archivos clave:
- `ventas/models.py` — `Venta` tiene campo `descuento` (Decimal, default=0)
- `ventas/services.py` — `VentaService.registrar()` aplica descuento como resta simple
- `ventas/dashboard_views.py:94-125` — `buscar_productos_venta()` busca en DB sin cache
- `config/settings.py` — No hay `CACHES` configurado
- `requirements.txt` — No hay `redis` ni `django-redis`
- `docker-compose.yml` — No hay servicio Redis

---

## Tarea 1: Strategy Pattern — Políticas de Descuento

### 1.1 Crear `core/descuentos.py` (o `ventas/descuentos.py`)

Crear una interfaz y las implementaciones:

```python
# core/descuentos.py
from abc import ABC, abstractmethod
from decimal import Decimal


class PoliticaDescuento(ABC):
    """Interfaz para políticas de descuento (Strategy Pattern)."""

    @abstractmethod
    def calcular(self, subtotal: Decimal, contexto: dict) -> Decimal:
        """
        Retorna el monto de descuento a aplicar.
        contexto puede incluir: usuario, productos, cantidades, etc.
        """
        ...


class DescuentoFijo(PoliticaDescuento):
    """Descuento de monto fijo ingresado por el cajero."""

    def calcular(self, subtotal: Decimal, contexto: dict) -> Decimal:
        monto = contexto.get("descuento_fijo", Decimal("0.00"))
        if monto < 0:
            monto = Decimal("0.00")
        return min(monto, subtotal)


class DescuentoPorcentaje(PoliticaDescuento):
    """Descuento por porcentaje del subtotal (ej: 10%)."""

    def calcular(self, subtotal: Decimal, contexto: dict) -> Decimal:
        porcentaje = contexto.get("porcentaje", Decimal("0"))
        if porcentaje <= 0 or porcentaje > 100:
            return Decimal("0.00")
        return (subtotal * porcentaje / 100).quantize(Decimal("0.01"))


class DescuentoClienteFrecuente(PoliticaDescuento):
    """Descuento del 5% para clientes frecuentes (simulado con campo en contexto)."""

    PORCENTAJE = Decimal("5")

    def calcular(self, subtotal: Decimal, contexto: dict) -> Decimal:
        if contexto.get("es_cliente_frecuente", False):
            return (subtotal * self.PORCENTAJE / 100).quantize(Decimal("0.01"))
        return Decimal("0.00")


class DescuentoPorVolumen(PoliticaDescuento):
    """Descuento escalonado según cantidad total de unidades."""

    def calcular(self, subtotal: Decimal, contexto: dict) -> Decimal:
        cantidad_total = contexto.get("cantidad_total", 0)
        if cantidad_total >= 100:
            porcentaje = Decimal("15")
        elif cantidad_total >= 50:
            porcentaje = Decimal("10")
        elif cantidad_total >= 20:
            porcentaje = Decimal("5")
        else:
            return Decimal("0.00")
        return (subtotal * porcentaje / 100).quantize(Decimal("0.01"))


class PrecioEspecial(PoliticaDescuento):
    """Precio especial por producto (ej: precio de mayoreo)."""

    def calcular(self, subtotal: Decimal, contexto: dict) -> Decimal:
        precio_especial = contexto.get("precio_especial_total", Decimal("0.00"))
        if precio_especial > 0 and precio_especial < subtotal:
            return subtotal - precio_especial
        return Decimal("0.00")
```

### 1.2 Crear un selector/factory de políticas

```python
# core/descuentos.py (al final del archivo)

POLITICAS = {
    "fijo": DescuentoFijo,
    "porcentaje": DescuentoPorcentaje,
    "cliente_frecuente": DescuentoClienteFrecuente,
    "volumen": DescuentoPorVolumen,
    "precio_especial": PrecioEspecial,
}


def obtener_politica(nombre: str) -> PoliticaDescuento:
    """Retorna una instancia de la política solicitada."""
    cls = POLITICAS.get(nombre)
    if cls is None:
        raise ValueError(f"Política de descuento desconocida: {nombre}")
    return cls()
```

### 1.3 Integrar en `VentaService.registrar()`

En `ventas/services.py`, modificar `registrar()` para usar la Strategy:

```python
# En ventas/services.py
from core.descuentos import obtener_politica

class VentaService:
    @classmethod
    @transaction.atomic
    def registrar(cls, usuario, caja_id, metodo_pago, descuento=None, detalles=None, politica_descuento=None, contexto_descuento=None):
        # ... (validaciones existentes) ...

        # Calcular subtotal
        subtotal = sum(d["precio_unitario"] * d["cantidad"] for d in detalles_data)

        # Aplicar política de descuento si se indica
        if politica_descuento:
            politica = obtener_politica(politica_descuento)
            descuento = politica.calcular(subtotal, contexto_descuento or {})
        elif descuento is None:
            descuento = Decimal("0.00")

        # ... resto del código existente ...
```

### 1.4 Agregar endpoint de prueba (opcional pero recomendado)

En `ventas/views.py`, agregar un action al `VentaViewSet`:

```python
@action(detail=False, methods=["get"], url_path="politicas-descuento")
def politicas_descuento(self, request):
    """Lista las políticas de descuento disponibles."""
    from core.descuentos import POLITICAS
    return Response({"politicas": list(POLITICAS.keys())})
```

---

## Tarea 2: Redis Cache para Búsqueda de Productos

### 2.1 Instalar dependencias

Agregar a `requirements.txt`:
```
django-redis==5.4.0
redis==5.0.8
```

### 2.2 Agregar servicio Redis en `docker-compose.yml`

```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: pos_redis
    restart: always
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  web:
    # ... (existente) ...
    depends_on:
      - db
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0

volumes:
  postgres_data:
  redis_data:
```

### 2.3 Configurar caché en `config/settings.py`

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/0"),
        "TIMEOUT": 300,  # 5 minutos
        "OPTIONS": {
            "db": "0",
        },
    }
}

# Cache key para búsqueda de productos
PRODUCTOS_CACHE_KEY = "productos:buscar"
PRODUCTOS_CACHE_TIMEOUT = 300  # 5 minutos
```

**Nota:** Django 4.0+ tiene `django.core.cache.backends.redis.RedisCache` integrado. No necesita `django-redis` si usás Django 5.2. Solo necesitás el paquete `redis` de Python.

### 2.4 Crear servicio de caché de productos

Crear `productos/cache.py`:

```python
import json
from decimal import Decimal
from django.core.cache import cache

PRODUCTOS_CACHE_KEY = "productos:buscar:{query}"
PRODUCTOS_CACHE_TIMEOUT = 300


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def get_cached_productos(query):
    """Busca productos en cache por query. Retorna None si no existe."""
    key = PRODUCTOS_CACHE_KEY.format(query=query.lower().strip())
    data = cache.get(key)
    if data is not None:
        return json.loads(data)
    return None


def set_cached_productos(query, productos_list):
    """Guarda resultados de búsqueda en cache."""
    key = PRODUCTOS_CACHE_KEY.format(query=query.lower().strip())
    data = json.dumps(productos_list, cls=DecimalEncoder)
    cache.set(key, data, PRODUCTOS_CACHE_TIMEOUT)


def invalidate_productos_cache():
    """Invalida todo el caché de productos (al crear/editar/eliminar)."""
    # Usar pattern delete si django-redis, sino limpiar keys conocidas
    cache.clear()
```

### 2.5 Integrar cache en la búsqueda de productos

En `ventas/dashboard_views.py`, modificar `buscar_productos_venta()`:

```python
from productos.cache import get_cached_productos, set_cached_productos

def buscar_productos_venta(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"productos": []})

    # Intentar cache primero
    cached = get_cached_productos(query)
    if cached is not None:
        return JsonResponse({"productos": cached})

    # Cache miss — buscar en DB
    from productos.models import Producto
    productos = Producto.objects.select_related("categoria").filter(
        models.Q(codigo_barra__icontains=query) |
        models.Q(nombre__icontains=query),
        activo=True,
    )[:20]

    resultados = [
        {
            "id": p.id,
            "codigo_barra": p.codigo_barra or "",
            "nombre": p.nombre,
            "precio_venta": float(p.precio_venta),
            "stock_actual": p.stock_actual,
            "unidad": p.unidad,
            "categoria": p.categoria.nombre if p.categoria else "",
        }
        for p in productos
    ]

    set_cached_productos(query, resultados)
    return JsonResponse({"productos": resultados})
```

### 2.6 Invalidar caché al modificar productos

En `productos/services.py`, agregar invalidación después de crear/actualizar/eliminar:

```python
from productos.cache import invalidate_productos_cache

class ProductoService:
    @classmethod
    def crear(cls, data):
        # ... código existente ...
        invalidate_productos_cache()
        return producto

    @classmethod
    def actualizar(cls, producto, data):
        # ... código existente ...
        invalidate_productos_cache()
        return producto

    @staticmethod
    def eliminar(producto):
        # ... código existente ...
        invalidate_productos_cache()
        return producto
```

### 2.7 También cachear la búsqueda API

En `productos/views.py`, la acción `buscar` del `ProductoViewSet` también debería usar el cache.

---

## Tarea 3: Testing de Strategy + Cache

Crear tests en `core/tests_descuentos.py` (o `ventas/tests.py`):

```python
from decimal import Decimal
from django.test import TestCase
from core.descuentos import (
    DescuentoFijo, DescuentoPorcentaje, DescuentoClienteFrecuente,
    DescuentoPorVolumen, PrecioEspecial, obtener_politica,
)


class DescuentoFijoTest(TestCase):
    def test_descuento_fijo(self):
        d = DescuentoFijo()
        self.assertEqual(d.calcular(Decimal("100"), {"descuento_fijo": Decimal("10")}), Decimal("10"))

    def test_no_supera_subtotal(self):
        d = DescuentoFijo()
        self.assertEqual(d.calcular(Decimal("50"), {"descuento_fijo": Decimal("100")}), Decimal("50"))


class DescuentoPorcentajeTest(TestCase):
    def test_10_por_ciento(self):
        d = DescuentoPorcentaje()
        self.assertEqual(d.calcular(Decimal("200"), {"porcentaje": Decimal("10")}), Decimal("20.00"))


class DescuentoClienteFrecuenteTest(TestCase):
    def test_es_frecuente(self):
        d = DescuentoClienteFrecuente()
        self.assertEqual(d.calcular(Decimal("100"), {"es_cliente_frecuente": True}), Decimal("5.00"))

    def test_no_es_frecuente(self):
        d = DescuentoClienteFrecuente()
        self.assertEqual(d.calcular(Decimal("100"), {"es_cliente_frecuente": False}), Decimal("0.00"))


class DescuentoPorVolumenTest(TestCase):
    def test_mas_de_100_unidades(self):
        d = DescuentoPorVolumen()
        self.assertEqual(d.calcular(Decimal("1000"), {"cantidad_total": 150}), Decimal("150.00"))

    def test_menos_de_20(self):
        d = DescuentoPorVolumen()
        self.assertEqual(d.calcular(Decimal("100"), {"cantidad_total": 10}), Decimal("0.00"))


class ObtenerPoliticaTest(TestCase):
    def test_politica_valida(self):
        self.assertIsInstance(obtener_politica("fijo"), DescuentoFijo)

    def test_politica_invalida(self):
        with self.assertRaises(ValueError):
            obtener_politica("no_existe")
```

---

## Checklist de Validación

- [ ] `core/descuentos.py` creado con 5 políticas + factory
- [ ] `VentaService.registrar()` integra Strategy Pattern
- [ ] `redis` agregado a `requirements.txt`
- [ ] Servicio Redis en `docker-compose.yml`
- [ ] `CACHES` configurado en `settings.py`
- [ ] `productos/cache.py` creado con get/set/invalidate
- [ ] `buscar_productos_venta()` usa cache
- [ ] `ProductoViewSet.buscar` usa cache
- [ ] Cache invalidado al crear/actualizar/eliminar productos
- [ ] Tests de Strategy Pattern escritos
- [ ] `docker compose up --build` levanta Redis correctamente
- [ ] Búsqueda de productos funciona con y sin cache

---

## Commits Convencionales Sugeridos

```
feat(core): implementar Strategy Pattern para políticas de descuento
feat(ventas): integrar Strategy de descuento en VentaService.registrar()
feat(infra): agregar servicio Redis en docker-compose.yml
feat(productos): implementar cache de búsqueda de productos con Redis
refactor(ventas): usar cache en buscar_productos_venta
refactor(productos): invalidar cache de productos al modificar
test(core): agregar tests para Strategy Pattern de descuentos
```

---

## ⚠️ CONTEXTO IMPORTANTE: Cambios de ModeloBase (commit acb3241 en develop)

> **Antes de empezar, pulled `develop` y lee esto.** Estos cambios ya están implementados y afectan directamente tu trabajo.

### Qué cambió en tus archivos clave

| Archivo | Cambio | Impacto en tu trabajo |
|---------|--------|----------------------|
| `ventas/models.py` | `Venta` ahora hereda de `ModeloBase` | `Venta` tiene `activo=True` por defecto, `creado_en`, `actualizado_en`. El campo `descuento` sigue existiendo |
| `ventas/services.py` | `VentaService.registrar()` usa los campos nuevos | Tu Strategy Pattern se integra AQUÍ — el descuento se calcula antes de crear la venta |
| `ventas/dashboard_views.py:270-305` | `buscar_productos_venta()` usa `Producto.objects.filter(activo=True)` | Tu cache de Redis se integra AQUÍ — cache first, DB fallback |
| `productos/models.py` | `Producto` hereda `ModeloBase` con `ManagerActivos` | `Producto.objects` ya filtra `activo=True` automáticamente |
| `core/models.py` | CREADO con `ModeloBase` | Acá van las estrategias de descuento que proponés en `core/descuentos.py` |

### Cómo integrar tu Strategy Pattern con VentaService

En `ventas/services.py`, el flujo actual de `registrar()` es:
1. Valida caja abierta
2. Valida stock
3. Calcula subtotal
4. Resta descuento simple ( campo `descuento` )
5. Crea venta + detalles + movimientos

Tu cambio: en el paso 4, en vez de restar un valor escalar, llamás a la Strategy:
```python
# Antes
descuento = Decimal(contexto.get("descuento", "0"))

# Después
if politica_descuento:
    from core.descuentos import obtener_politica
    politica = obtener_politica(politica_descuento)
    descuento = politica.calcular(subtotal, contexto_descuento or {})
else:
    descuento = Decimal(contexto.get("descuento", "0"))
```

### Redis Cache — qué necesitás

1. Agregar `redis==5.0.8` a `requirements.txt`
2. Agregar servicio Redis en `docker-compose.yml` (servicio `redis` con imagen `redis:7-alpine`)
3. Configurar `CACHES` en `config/settings.py` usando `django.core.cache.backends.redis.RedisCache` (Django 5.2 ya lo trae integrado)
4. Crear `productos/cache.py` con `get_cached_productos()`, `set_cached_productos()`, `invalidate_productos_cache()`
5. Integrar en `buscar_productos_venta()` y `buscar` action de `ProductoViewSet`

### Anti-patrones a NO crear

- NO uses `created_at` / `updated_at` — los campos ahora se llaman `creado_en` / `actualizado_en`
- NO hagas `Venta.objects.filter(activo=False)` — usá `Venta.all_objects.filter(activo=False)`
