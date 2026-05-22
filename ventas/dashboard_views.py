from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q, Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from caja.models import Caja, MovimientoCaja
from productos.models import Producto
from .models import DetalleVenta, Venta


def _ventas_queryset(request):
    fecha = request.GET.get("fecha", "").strip()
    estado = request.GET.get("estado", "").strip()

    queryset = Venta.objects.select_related("cajero", "caja")
    if request.user.rol != "admin":
        queryset = queryset.filter(cajero=request.user)

    if fecha:
        queryset = queryset.filter(fecha__date=fecha)
    else:
        queryset = queryset.filter(fecha__date=timezone.localdate())

    if estado:
        queryset = queryset.filter(estado=estado)

    return queryset.order_by("-fecha"), {"fecha": fecha, "estado": estado}


def _venta_resumen(queryset):
    resumen = queryset.aggregate(
        total_general=Sum("total"),
        cantidad=Count("id"),
        efectivo=Sum("total", filter=Q(metodo_pago="EFECTIVO", estado="COMPLETADA")),
        tarjeta=Sum("total", filter=Q(metodo_pago="TARJETA", estado="COMPLETADA")),
        transferencia=Sum("total", filter=Q(metodo_pago="TRANSFERENCIA", estado="COMPLETADA")),
    )
    return {
        "total": resumen["total_general"] or Decimal("0.00"),
        "cantidad": resumen["cantidad"] or 0,
        "efectivo": resumen["efectivo"] or Decimal("0.00"),
        "tarjeta": resumen["tarjeta"] or Decimal("0.00"),
        "transferencia": resumen["transferencia"] or Decimal("0.00"),
    }


def _top_productos(queryset):
    return (
        DetalleVenta.objects.filter(venta__in=queryset, venta__estado="COMPLETADA")
        .values("producto__nombre")
        .annotate(cantidad=Sum("cantidad"))
        .order_by("-cantidad", "producto__nombre")[:5]
    )


@method_decorator(login_required, name="dispatch")
class VentaDashboardView(View):
    def get(self, request):
        queryset, filters_ctx = _ventas_queryset(request)
        paginator = Paginator(queryset, 12)
        page_obj = paginator.get_page(request.GET.get("page", 1))

        context = {
            "ventas": page_obj.object_list,
            "page_obj": page_obj,
            "filters": filters_ctx,
            "stats": _venta_resumen(queryset),
            "top_productos": _top_productos(queryset),
            "estados": Venta.ESTADO_CHOICES,
        }
        return render(request, "dashboard/ventas.html", context)


@method_decorator(login_required, name="dispatch")
class NuevaVentaView(View):
    def get(self, request):
        productos = Producto.objects.select_related("categoria").filter(activo=True, stock_actual__gt=0).order_by("nombre")
        cajas = Caja.objects.filter(estado="ABIERTA")
        if request.user.rol != "admin":
            cajas = cajas.filter(cajero=request.user)

        context = {
            "productos": productos[:30],
            "cajas_abiertas": cajas,
            "metodos_pago": Venta.METODO_PAGO_CHOICES,
        }
        return render(request, "dashboard/nueva_venta.html", context)


@method_decorator(login_required, name="dispatch")
class CajaDashboardView(View):
    def get(self, request):
        cajas = Caja.objects.select_related("cajero").prefetch_related(
            Prefetch("movimientos", queryset=MovimientoCaja.objects.select_related("usuario").order_by("-fecha"))
        )
        if request.user.rol != "admin":
            cajas = cajas.filter(cajero=request.user)

        caja_actual = cajas.order_by("-fecha_apertura").first()
        movimientos = caja_actual.movimientos.all()[:10] if caja_actual else []
        historial = cajas.order_by("-fecha_apertura")[:5]

        context = {
            "caja_actual": caja_actual,
            "movimientos": movimientos,
            "historial": historial,
        }
        return render(request, "dashboard/caja.html", context)
