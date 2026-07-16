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
