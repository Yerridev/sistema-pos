"""Strategy Pattern para políticas de descuento.

Define una interfaz común (``PoliticaDescuento``) y varias implementaciones
intercambiables. ``VentaService.registrar()`` selecciona la política en tiempo
de ejecución mediante ``obtener_politica()`` sin acoplarse a una fórmula
concreta de descuento.
"""

from abc import ABC, abstractmethod
from decimal import Decimal

CENTIMOS = Decimal("0.01")


class PoliticaDescuento(ABC):
    """Interfaz para políticas de descuento (Strategy Pattern)."""

    @abstractmethod
    def calcular(self, subtotal: Decimal, contexto: dict) -> Decimal:
        """Retorna el monto de descuento a aplicar sobre ``subtotal``.

        Args:
            subtotal: importe base sobre el que se calcula el descuento.
            contexto: datos adicionales de la venta (usuario, cantidades,
                banderas de negocio, etc.).
        """
        ...


class DescuentoFijo(PoliticaDescuento):
    """Descuento de monto fijo ingresado por el cajero."""

    def calcular(self, subtotal: Decimal, contexto: dict) -> Decimal:
        monto = contexto.get("descuento_fijo", Decimal("0.00"))
        monto = Decimal(str(monto))
        if monto < 0:
            monto = Decimal("0.00")
        return min(monto, subtotal)


class DescuentoPorcentaje(PoliticaDescuento):
    """Descuento por porcentaje del subtotal (ej: 10%)."""

    def calcular(self, subtotal: Decimal, contexto: dict) -> Decimal:
        porcentaje = Decimal(str(contexto.get("porcentaje", 0)))
        if porcentaje <= 0 or porcentaje > 100:
            return Decimal("0.00")
        return (subtotal * porcentaje / 100).quantize(CENTIMOS)


class DescuentoClienteFrecuente(PoliticaDescuento):
    """Descuento del 5% para clientes frecuentes."""

    PORCENTAJE = Decimal("5")

    def calcular(self, subtotal: Decimal, contexto: dict) -> Decimal:
        if contexto.get("es_cliente_frecuente", False):
            return (subtotal * self.PORCENTAJE / 100).quantize(CENTIMOS)
        return Decimal("0.00")


class DescuentoPorVolumen(PoliticaDescuento):
    """Descuento escalonado según la cantidad total de unidades."""

    def calcular(self, subtotal: Decimal, contexto: dict) -> Decimal:
        cantidad_total = int(contexto.get("cantidad_total", 0))
        if cantidad_total >= 100:
            porcentaje = Decimal("15")
        elif cantidad_total >= 50:
            porcentaje = Decimal("10")
        elif cantidad_total >= 20:
            porcentaje = Decimal("5")
        else:
            return Decimal("0.00")
        return (subtotal * porcentaje / 100).quantize(CENTIMOS)


class PrecioEspecial(PoliticaDescuento):
    """Precio especial por producto (ej: precio de mayoreo)."""

    def calcular(self, subtotal: Decimal, contexto: dict) -> Decimal:
        precio_especial = Decimal(str(contexto.get("precio_especial_total", 0)))
        if precio_especial > 0 and precio_especial < subtotal:
            return (subtotal - precio_especial).quantize(CENTIMOS)
        return Decimal("0.00")


POLITICAS = {
    "fijo": DescuentoFijo,
    "porcentaje": DescuentoPorcentaje,
    "cliente_frecuente": DescuentoClienteFrecuente,
    "volumen": DescuentoPorVolumen,
    "precio_especial": PrecioEspecial,
}

# Etiquetas legibles para exponer las politicas en la UI (dashboard) y en el
# endpoint GET /api/ventas/politicas-descuento/. Unico punto de verdad para
# los nombres visibles: agregar una politica nueva aqui basta para que
# aparezca en ambos lugares sin tocar el frontend.
POLITICAS_LABELS = {
    "fijo": "Descuento en soles (monto fijo)",
    "porcentaje": "Descuento por porcentaje",
    "cliente_frecuente": "Cliente frecuente (5% automatico)",
    "volumen": "Descuento por cantidad comprada (automatico)",
    "precio_especial": "Precio especial acordado con el cliente",
}


def obtener_politica(nombre: str) -> PoliticaDescuento:
    """Retorna una instancia de la política solicitada.

    Raises:
        ValueError: si el nombre no corresponde a ninguna política registrada.
    """
    cls = POLITICAS.get(nombre)
    if cls is None:
        raise ValueError(f"Política de descuento desconocida: {nombre}")
    return cls()
