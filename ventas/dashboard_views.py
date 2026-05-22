from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
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
from productos.models import Producto
from .models import DetalleVenta, Venta


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

        context = {
            "ventas": page_obj.object_list,
            "page_obj": page_obj,
            "filters": filters_ctx,
            "stats": _venta_resumen(queryset),
            "top_productos": _top_productos(queryset),
            "estados": Venta.ESTADO_CHOICES,
        }
        return render(request, "dashboard/ventas.html", context)


@login_required
def buscar_productos_venta(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"results": []})

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

    return JsonResponse({
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
    })


@method_decorator(login_required, name="dispatch")
class NuevaVentaView(View):
    def get(self, request):
        cajas = Caja.objects.filter(estado="ABIERTA")
        if request.user.rol != "admin":
            cajas = cajas.filter(cajero=request.user)

        context = {
            "cajas_abiertas": cajas,
            "metodos_pago": Venta.METODO_PAGO_CHOICES,
        }
        return render(request, "dashboard/nueva_venta.html", context)

    @transaction.atomic
    def post(self, request):
        caja_id = request.POST.get("caja")
        metodo_pago = request.POST.get("metodo_pago")
        descuento = request.POST.get("descuento", "0").strip() or "0"
        detalles = self._parse_cart_items(request)

        if metodo_pago not in dict(Venta.METODO_PAGO_CHOICES):
            messages.error(request, "Selecciona un metodo de pago valido.")
            return redirect("ventas:nueva_venta")

        try:
            descuento = Decimal(descuento)
            if descuento < 0:
                raise ValueError
        except Exception:
            messages.error(request, "El descuento debe ser un numero positivo.")
            return redirect("ventas:nueva_venta")

        try:
            caja = Caja.objects.select_for_update().get(pk=caja_id, estado="ABIERTA")
        except Caja.DoesNotExist:
            messages.error(request, "Selecciona una caja abierta.")
            return redirect("ventas:nueva_venta")

        if caja.cajero_id != request.user.id and request.user.rol != "admin":
            messages.error(request, "No puedes vender en una caja de otro cajero.")
            return redirect("ventas:nueva_venta")

        if not detalles:
            messages.error(request, "Agrega productos al carrito antes de confirmar la venta.")
            return redirect("ventas:nueva_venta")

        venta = Venta.objects.create(
            cajero=request.user,
            caja=caja,
            metodo_pago=metodo_pago,
            descuento=descuento,
        )

        for producto_id, cantidad in detalles:
            try:
                producto = Producto.objects.select_for_update().get(pk=producto_id, activo=True)
            except Producto.DoesNotExist:
                transaction.set_rollback(True)
                messages.error(request, "Uno de los productos seleccionados no existe.")
                return redirect("ventas:nueva_venta")

            if producto.stock_actual < cantidad:
                transaction.set_rollback(True)
                messages.error(request, f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock_actual}.")
                return redirect("ventas:nueva_venta")

            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=producto.precio_venta,
            )
            producto.stock_actual -= cantidad
            producto.save(update_fields=["stock_actual"])

        venta.calcular_totales()
        MovimientoCaja.objects.create(
            caja=caja,
            tipo="INGRESO",
            monto=venta.total,
            concepto=f"Venta #{venta.id}",
            usuario=request.user,
        )
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

        return render(request, "dashboard/detalle_venta.html", {"venta": venta})


@login_required
@require_POST
@transaction.atomic
def anular_venta_dashboard(request, pk):
    venta = get_object_or_404(
        Venta.objects.select_for_update().select_related("cajero", "caja"),
        pk=pk,
    )

    if not _user_can_access_venta(request.user, venta):
        messages.error(request, "No puedes anular una venta de otro cajero.")
        return redirect("ventas:dashboard")
    if venta.estado == "ANULADA":
        messages.error(request, "La venta ya se encuentra anulada.")
        return redirect("ventas:detalle_venta", pk=venta.pk)

    motivo = request.POST.get("motivo", "").strip() or "Anulacion desde detalle de venta"

    venta.estado = "ANULADA"
    venta.motivo_anulacion = motivo
    venta.anulado_por = request.user
    venta.fecha_anulacion = timezone.now()
    venta.save(update_fields=["estado", "motivo_anulacion", "anulado_por", "fecha_anulacion"])

    detalles = DetalleVenta.objects.select_related("producto").select_for_update().filter(venta=venta)
    for detalle in detalles:
        detalle.producto.stock_actual += detalle.cantidad
        detalle.producto.save(update_fields=["stock_actual"])

    MovimientoCaja.objects.create(
        caja=venta.caja,
        tipo="EGRESO",
        monto=venta.total,
        concepto=f"Anulacion venta #{venta.id}: {motivo}",
        usuario=request.user,
    )

    messages.success(request, f"Venta #{venta.id} anulada correctamente. El stock fue devuelto.")
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
        movimientos = caja_actual.movimientos.all()[:10] if caja_actual else []
        historial = cajas.order_by("-fecha_apertura")[:5]

        context = {
            "caja_actual": caja_actual,
            "movimientos": movimientos,
            "historial": historial,
        }
        return render(request, "dashboard/caja.html", context)


@login_required
@require_POST
def abrir_caja(request):
    if Caja.objects.filter(cajero=request.user, estado="ABIERTA").exists():
        messages.error(request, "Ya tienes una caja abierta.")
        return redirect("ventas:caja_dashboard")

    nombre = request.POST.get("nombre", "").strip() or f"Caja {request.user.username}"
    saldo_inicial = request.POST.get("saldo_inicial", "0").strip() or "0"

    try:
        saldo_inicial = Decimal(saldo_inicial)
        if saldo_inicial < 0:
            raise ValueError
    except Exception:
        messages.error(request, "El saldo inicial debe ser un numero positivo.")
        return redirect("ventas:caja_dashboard")

    Caja.objects.create(
        nombre=nombre,
        saldo_inicial=saldo_inicial,
        cajero=request.user,
        estado="ABIERTA",
    )
    messages.success(request, "Caja abierta correctamente.")
    return redirect("ventas:caja_dashboard")


@login_required
@require_POST
def cerrar_caja(request, pk):
    caja = Caja.objects.filter(pk=pk).first()
    if not caja:
        messages.error(request, "La caja no existe.")
        return redirect("ventas:caja_dashboard")
    if caja.cajero_id != request.user.id and request.user.rol != "admin":
        messages.error(request, "No puedes cerrar una caja de otro cajero.")
        return redirect("ventas:caja_dashboard")
    if caja.estado != "ABIERTA":
        messages.error(request, "Solo se puede cerrar una caja abierta.")
        return redirect("ventas:caja_dashboard")

    caja.saldo_final = caja.saldo_actual
    caja.fecha_cierre = timezone.now()
    caja.estado = "CERRADA"
    caja.save(update_fields=["saldo_final", "fecha_cierre", "estado"])
    messages.success(request, "Caja cerrada correctamente.")
    return redirect("ventas:caja_dashboard")


@login_required
@require_POST
def registrar_movimiento_caja(request, pk):
    caja = Caja.objects.filter(pk=pk).first()
    if not caja:
        messages.error(request, "La caja no existe.")
        return redirect("ventas:caja_dashboard")
    if caja.cajero_id != request.user.id and request.user.rol != "admin":
        messages.error(request, "No puedes registrar movimientos en esta caja.")
        return redirect("ventas:caja_dashboard")
    if caja.estado != "ABIERTA":
        messages.error(request, "Solo se registran movimientos en cajas abiertas.")
        return redirect("ventas:caja_dashboard")

    tipo = request.POST.get("tipo", "").strip()
    concepto = request.POST.get("concepto", "").strip()
    monto = request.POST.get("monto", "").strip()

    if tipo not in {"INGRESO", "EGRESO"}:
        messages.error(request, "Selecciona un tipo de movimiento valido.")
        return redirect("ventas:caja_dashboard")
    if not concepto:
        messages.error(request, "El concepto del movimiento es obligatorio.")
        return redirect("ventas:caja_dashboard")

    try:
        monto = Decimal(monto)
        if monto <= 0:
            raise ValueError
    except Exception:
        messages.error(request, "El monto debe ser mayor que cero.")
        return redirect("ventas:caja_dashboard")

    MovimientoCaja.objects.create(
        caja=caja,
        tipo=tipo,
        monto=monto,
        concepto=concepto,
        usuario=request.user,
    )
    messages.success(request, "Movimiento registrado correctamente.")
    return redirect("ventas:caja_dashboard")
