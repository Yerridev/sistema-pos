from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q, Sum
from django.contrib import messages
import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from caja.models import Caja, MovimientoCaja
from caja.services import CajaService
from core.exceptions import AppError
from productos.cache import get_cached_productos, set_cached_productos
from productos.models import Producto
from .models import DetalleVenta, Venta
from .services import VentaService


def _user_can_access_venta(user, venta):
    return venta.cajero_id == user.id or getattr(user, "rol", None) == "admin"


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

        pagination_parts = []
        if filters_ctx.get("fecha"):
            pagination_parts.append(f"fecha={filters_ctx['fecha']}")
        if filters_ctx.get("estado"):
            pagination_parts.append(f"estado={filters_ctx['estado']}")
        pagination_query = "&".join(pagination_parts)

        context = {
            "ventas": page_obj.object_list,
            "page_obj": page_obj,
            "filters": filters_ctx,
            "pagination_query": pagination_query,
            "stats": _venta_resumen(queryset),
            "top_productos": _top_productos(queryset),
            "estados": Venta.ESTADO_CHOICES,
            "page_title": "Ventas",
            "active_nav": "ventas:dashboard",
        }
        return render(request, "dashboard/ventas.html", context)


@login_required
def buscar_productos_venta(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"results": []})

    # Cache first: la búsqueda por código/nombre se repite en cada tecleo.
    cached = get_cached_productos(query, scope="venta")
    if cached is not None:
        return JsonResponse(cached)

    productos = Producto.objects.select_related("categoria").filter(activo=True, stock_actual__gt=0)
    exact_barcode = productos.filter(codigo_barra__iexact=query).first()

    if exact_barcode:
        results = [exact_barcode]
        match_type = "barcode"
    else:
        results = productos.filter(
            Q(nombre__icontains=query) | Q(codigo_barra__icontains=query)
        ).order_by("nombre")[:10]
        match_type = "search"

    payload = {
        "match_type": match_type,
        "results": [
            {
                "id": producto.id,
                "codigo_barra": producto.codigo_barra or "",
                "nombre": producto.nombre,
                "categoria": producto.categoria.nombre,
                "precio_venta": str(producto.precio_venta),
                "stock_actual": producto.stock_actual,
                "unidad": producto.unidad,
            }
            for producto in results
        ],
    }
    set_cached_productos(query, payload, scope="venta")
    return JsonResponse(payload)


@method_decorator(login_required, name="dispatch")
class NuevaVentaView(View):
    def get(self, request):
        cajas = Caja.objects.filter(estado="ABIERTA")
        if request.user.rol != "admin":
            cajas = cajas.filter(cajero=request.user)

        context = {
            "cajas_abiertas": cajas,
            "metodos_pago": Venta.METODO_PAGO_CHOICES,
            "page_title": "Nueva Venta",
            "active_nav": "ventas:nueva_venta",
        }
        return render(request, "dashboard/nueva_venta.html", context)

    def post(self, request):
        metodo_pago = request.POST.get("metodo_pago")
        if metodo_pago not in dict(Venta.METODO_PAGO_CHOICES):
            messages.error(request, "Selecciona un metodo de pago valido.")
            return redirect("ventas:nueva_venta")

        detalles_raw = self._parse_cart_items(request)
        if not detalles_raw:
            messages.error(request, "Agrega productos al carrito antes de confirmar la venta.")
            return redirect("ventas:nueva_venta")

        try:
            descuento = Decimal(request.POST.get("descuento", "0").strip() or "0")
        except Exception:
            messages.error(request, "El descuento debe ser un numero valido.")
            return redirect("ventas:nueva_venta")

        detalles = [{"producto": pid, "cantidad": qty} for pid, qty in detalles_raw]
        try:
            venta = VentaService.registrar(
                usuario=request.user,
                caja_id=request.POST.get("caja"),
                metodo_pago=metodo_pago,
                descuento=descuento,
                detalles=detalles,
            )
        except AppError as exc:
            messages.error(request, str(exc))
            return redirect("ventas:nueva_venta")

        messages.success(request, f"Venta #{venta.id} registrada correctamente por S/. {venta.total}.")
        return redirect("ventas:detalle_venta", pk=venta.pk)

    def _parse_cart_items(self, request):
        cart_items = request.POST.get("cart_items", "").strip()
        if cart_items:
            try:
                payload = json.loads(cart_items)
            except (TypeError, ValueError):
                return []
            detalles = []
            for item in payload:
                try:
                    producto_id = int(item.get("producto_id"))
                    cantidad = int(item.get("cantidad", 0))
                except (TypeError, ValueError):
                    continue
                if cantidad > 0:
                    detalles.append((producto_id, cantidad))
            return detalles

        detalles = []
        for key, value in request.POST.items():
            if not key.startswith("cantidad_"):
                continue
            try:
                cantidad = int(value or 0)
            except ValueError:
                cantidad = 0
            if cantidad <= 0:
                continue
            producto_id = key.replace("cantidad_", "", 1)
            detalles.append((producto_id, cantidad))
        return detalles


@method_decorator(login_required, name="dispatch")
class VentaDetalleDashboardView(View):
    def get(self, request, pk):
        venta = get_object_or_404(
            Venta.objects.select_related("cajero", "caja").prefetch_related("detalles__producto"),
            pk=pk,
        )
        if venta.cajero_id != request.user.id and request.user.rol != "admin":
            messages.error(request, "No puedes ver el detalle de una venta de otro cajero.")
            return redirect("ventas:dashboard")

        return render(request, "dashboard/detalle_venta.html", {"venta": venta, "page_title": f"Venta #{venta.id}", "active_nav": "ventas:dashboard"})


@login_required
@require_POST
def anular_venta_dashboard(request, pk):
    venta = get_object_or_404(
        Venta.objects.select_related("cajero", "caja"),
        pk=pk,
    )

    if not _user_can_access_venta(request.user, venta):
        messages.error(request, "No puedes anular una venta de otro cajero.")
        return redirect("ventas:dashboard")

    motivo = request.POST.get("motivo", "").strip() or "Anulacion desde detalle de venta"
    try:
        VentaService.anular(venta=venta, usuario=request.user, motivo=motivo)
        messages.success(request, f"Venta #{venta.id} anulada correctamente. El stock fue devuelto.")
    except AppError as exc:
        messages.error(request, str(exc))

    return redirect("ventas:detalle_venta", pk=venta.pk)


@method_decorator(login_required, name="dispatch")
class CajaDashboardView(View):
    def get(self, request):
        cajas = Caja.objects.select_related("cajero").prefetch_related(
            Prefetch("movimientos", queryset=MovimientoCaja.objects.select_related("usuario").order_by("-fecha"))
        )
        if request.user.rol != "admin":
            cajas = cajas.filter(cajero=request.user)

        caja_actual = cajas.filter(estado="ABIERTA").order_by("-fecha_apertura").first()
        movimientos_qs = caja_actual.movimientos.all() if caja_actual else MovimientoCaja.objects.none()
        paginator = Paginator(movimientos_qs, 10)
        movimientos_page = paginator.get_page(request.GET.get("page", 1))
        historial = cajas.order_by("-fecha_apertura")[:5]

        context = {
            "caja_actual": caja_actual,
            "movimientos": movimientos_page.object_list,
            "page_obj": movimientos_page,
            "historial": historial,
            "page_title": "Caja",
            "active_nav": "ventas:caja_dashboard",
        }
        return render(request, "dashboard/caja.html", context)


@login_required
@require_POST
def abrir_caja(request):
    nombre = request.POST.get("nombre", "").strip() or f"Caja {request.user.username}"
    saldo_raw = request.POST.get("saldo_inicial", "0").strip() or "0"

    try:
        saldo_inicial = Decimal(saldo_raw)
        if saldo_inicial < 0:
            raise ValueError
    except (ValueError, TypeError, InvalidOperation):
        messages.error(request, "El saldo inicial debe ser un numero positivo.")
        return redirect("ventas:caja_dashboard")

    try:
        CajaService.abrir(usuario=request.user, nombre=nombre, saldo_inicial=saldo_inicial)
        messages.success(request, "Caja abierta correctamente.")
    except AppError as exc:
        messages.error(request, str(exc))

    return redirect("ventas:caja_dashboard")


@login_required
@require_POST
def cerrar_caja(request, pk):
    caja = Caja.objects.filter(pk=pk).first()
    if not caja:
        messages.error(request, "La caja no existe.")
        return redirect("ventas:caja_dashboard")

    try:
        CajaService.cerrar(caja=caja, usuario=request.user)
        messages.success(request, "Caja cerrada correctamente.")
    except AppError as exc:
        messages.error(request, str(exc))

    return redirect("ventas:caja_dashboard")


@login_required
@require_POST
def registrar_movimiento_caja(request, pk):
    caja = Caja.objects.filter(pk=pk).first()
    if not caja:
        messages.error(request, "La caja no existe.")
        return redirect("ventas:caja_dashboard")

    tipo = request.POST.get("tipo", "").strip()
    concepto = request.POST.get("concepto", "").strip()
    monto_raw = request.POST.get("monto", "").strip()

    if not concepto:
        messages.error(request, "El concepto del movimiento es obligatorio.")
        return redirect("ventas:caja_dashboard")

    try:
        monto = Decimal(monto_raw)
        if monto <= 0:
            raise ValueError
    except (ValueError, TypeError, InvalidOperation):
        messages.error(request, "El monto debe ser mayor que cero.")
        return redirect("ventas:caja_dashboard")

    try:
        CajaService.registrar_movimiento(
            caja=caja, usuario=request.user, tipo=tipo, monto=monto, concepto=concepto
        )
        messages.success(request, "Movimiento registrado correctamente.")
    except AppError as exc:
        messages.error(request, str(exc))

    return redirect("ventas:caja_dashboard")
