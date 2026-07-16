"""Cache de búsqueda de productos con Redis.

Envuelve el framework de cache de Django (configurado con Redis en
``config.settings``) para memorizar los resultados de búsqueda de productos y
evitar golpear PostgreSQL en cada tecleo del cajero. Ante cualquier fallo del
backend de cache las funciones degradan de forma segura (la búsqueda sigue
funcionando contra la base de datos).
"""

from django.conf import settings
from django.core.cache import cache

PRODUCTOS_CACHE_PREFIX = "productos:buscar"
PRODUCTOS_CACHE_TIMEOUT = getattr(settings, "PRODUCTOS_CACHE_TIMEOUT", 300)


def _make_key(query, scope="default"):
    """Construye la clave de cache normalizando el término de búsqueda."""
    return f"{PRODUCTOS_CACHE_PREFIX}:{scope}:{query.lower().strip()}"


def get_cached_productos(query, scope="default"):
    """Retorna los resultados cacheados para ``query`` o ``None`` si no existen."""
    try:
        return cache.get(_make_key(query, scope))
    except Exception:
        return None


def set_cached_productos(query, resultados, scope="default"):
    """Guarda en cache los resultados de una búsqueda."""
    try:
        cache.set(_make_key(query, scope), resultados, PRODUCTOS_CACHE_TIMEOUT)
    except Exception:
        pass


def invalidate_productos_cache():
    """Invalida el cache de productos al crear/editar/eliminar un producto."""
    try:
        cache.clear()
    except Exception:
        pass
