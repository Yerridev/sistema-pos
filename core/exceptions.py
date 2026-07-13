"""
Jerarquía de excepciones de dominio para el Sistema POS.

Todas las excepciones de negocio descienden de ``AppError`` para que las
views puedan capturarlas de forma uniforme y traducirlas al response que
corresponda (``Response`` JSON en DRF, ``messages.error`` + redirect en
templates Django).

Jerarquía::

    AppError
    ├── ReglaNegocioViolada
    │   ├── CajaNoAbierta
    │   ├── CajaYaAbierta
    │   ├── CajaAjena
    │   ├── ProductoSinStock
    │   ├── MargenInvalidoError
    │   └── VentaYaAnulada
    ├── RecursoNoEncontrado
    └── AccesoNoAutorizado
"""


class AppError(Exception):
    """Base de todas las excepciones de la aplicación."""


# ── Categorías principales ────────────────────────────────────────────────


class ReglaNegocioViolada(AppError):
    """Se intentó ejecutar una operación que rompe una regla de negocio."""


class RecursoNoEncontrado(AppError):
    """El recurso solicitado no existe."""


class AccesoNoAutorizado(AppError):
    """El usuario no tiene permiso para realizar la operación."""


# ── Excepciones específicas del dominio ───────────────────────────────────


class CajaNoAbierta(ReglaNegocioViolada):
    """La caja no está ABIERTA y se requiere que lo esté."""


class CajaYaAbierta(ReglaNegocioViolada):
    """Ya existe una caja ABIERTA para el cajero."""


class CajaAjena(AccesoNoAutorizado):
    """Se intentó operar sobre una caja que pertenece a otro cajero."""


class ProductoSinStock(ReglaNegocioViolada):
    """No hay stock suficiente para completar la venta."""


class MargenInvalidoError(ReglaNegocioViolada):
    """El precio de venta es menor al costo (margen negativo)."""


class VentaYaAnulada(ReglaNegocioViolada):
    """Se intentó anular una venta que ya está anulada."""
