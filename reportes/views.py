from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers

from caja.models import Caja
from reportes.permissions import IsAdminUser
from reportes.services import ReporteService


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
@permission_classes([IsAuthenticated, IsAdminUser])
def ventas_del_dia_api(request):
    data = ReporteService.ventas_del_dia(_parse_date(request, "fecha", timezone.localdate()))
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
@permission_classes([IsAuthenticated, IsAdminUser])
def stock_critico_api(request):
    return Response({"results": ReporteService.stock_critico()})


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
@permission_classes([IsAuthenticated, IsAdminUser])
def utilidad_api(request):
    data = ReporteService.utilidad(_parse_date(request, "desde"), _parse_date(request, "hasta"))
    return Response(data)


@login_required
@user_passes_test(_is_admin)
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


@login_required
@user_passes_test(_is_admin)
def admin_dashboard(request):
    """Dashboard principal del admin con metricas clave."""
    fecha = timezone.localdate()

    ventas_data = ReporteService.ventas_del_dia(fecha)

    cajas_abiertas = Caja.objects.filter(estado="ABIERTA").select_related("cajero")
    cajas_info = []
    for caja in cajas_abiertas:
        cajas_info.append({
            "id": caja.id,
            "nombre": caja.nombre,
            "cajero": caja.cajero.get_full_name() or caja.cajero.username,
            "saldo_actual": caja.saldo_actual,
            "fecha_apertura": caja.fecha_apertura,
        })

    stock_critico = ReporteService.stock_critico()

    return render(request, "dashboard/admin_dashboard.html", {
        "ventas_dia": ventas_data,
        "cajas_abiertas": cajas_info,
        "stock_critico": stock_critico,
        "page_title": "Dashboard Admin",
        "active_nav": "reportes:admin_dashboard",
    })
