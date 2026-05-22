from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers

from productos.models import Producto
from ventas.models import DetalleVenta, Venta


def _is_admin(user):
    return bool(user and user.is_authenticated and getattr(user, "rol", None) == "admin")


def _parse_date(request, key, default=None):
    value = request.GET.get(key)
    if not value:
        return default
    try:
        return timezone.datetime.fromisoformat(value).date()
    except ValueError:
        return default


def ventas_del_dia_data(fecha=None):
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


def stock_critico_data():
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


def utilidad_data(desde=None, hasta=None):
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


@extend_schema(
    parameters=[OpenApiParameter("fecha", str, OpenApiParameter.QUERY)],
    responses=inline_serializer(
        name="VentasDelDiaReporte",
        fields={
            "fecha": serializers.DateField(),
            "total": serializers.DecimalField(max_digits=10, decimal_places=2),
            "cantidad": serializers.IntegerField(),
            "por_metodo": serializers.DictField(),
            "top_productos": serializers.ListField(),
        },
    ),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ventas_del_dia_api(request):
    data = ventas_del_dia_data(_parse_date(request, "fecha", timezone.localdate()))
    return Response({
        "fecha": data["fecha"],
        "total": data["total"],
        "cantidad": data["cantidad"],
        "por_metodo": data["por_metodo"],
        "top_productos": data["top_productos"],
    })


@extend_schema(
    responses=inline_serializer(
        name="StockCriticoReporte",
        fields={"results": serializers.ListField()},
    ),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stock_critico_api(request):
    return Response({"results": stock_critico_data()})


@extend_schema(
    parameters=[
        OpenApiParameter("desde", str, OpenApiParameter.QUERY),
        OpenApiParameter("hasta", str, OpenApiParameter.QUERY),
    ],
    responses=inline_serializer(
        name="UtilidadReporte",
        fields={
            "desde": serializers.DateField(allow_null=True),
            "hasta": serializers.DateField(allow_null=True),
            "ingresos": serializers.DecimalField(max_digits=10, decimal_places=2),
            "costos": serializers.DecimalField(max_digits=10, decimal_places=2),
            "utilidad": serializers.DecimalField(max_digits=10, decimal_places=2),
            "por_dia": serializers.ListField(),
        },
    ),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def utilidad_api(request):
    if not _is_admin(request.user):
        return Response({"detail": "Solo admin puede ver utilidad."}, status=403)
    data = utilidad_data(_parse_date(request, "desde"), _parse_date(request, "hasta"))
    return Response(data)


@login_required
@user_passes_test(_is_admin)
def reportes_dashboard(request):
    fecha = _parse_date(request, "fecha", timezone.localdate())
    desde = _parse_date(request, "desde")
    hasta = _parse_date(request, "hasta")
    return render(request, "dashboard/reportes.html", {
        "ventas_dia": ventas_del_dia_data(fecha),
        "stock_critico": stock_critico_data(),
        "utilidad": utilidad_data(desde, hasta),
        "filters": {"fecha": fecha, "desde": desde, "hasta": hasta},
    })
