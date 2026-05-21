from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from caja.models import Caja, MovimientoCaja
from productos.models import Producto
from .models import DetalleVenta, Venta
from .serializers import VentaCreateSerializer


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
        cajas = Caja.objects.filter(estado="ABIERTA")
        if request.user.rol != "admin":
            cajas = cajas.filter(cajero=request.user)
        if not cajas.exists():
            messages.warning(request, "No tienes caja abierta. Abre una caja antes de registrar ventas.")

        context = {
            "cajas_abiertas": cajas,
            "metodos_pago": Venta.METODO_PAGO_CHOICES,
        }
        return render(request, "dashboard/nueva_venta.html", context)

    def post(self, request):
        producto_id = request.POST.get("producto_id")
        cantidad = request.POST.get("cantidad", "1")
        caja_id = request.POST.get("caja_id")
        metodo_pago = request.POST.get("metodo_pago", "EFECTIVO")
        descuento = request.POST.get("descuento", "0")

        payload = {
            "caja_id": caja_id,
            "metodo_pago": metodo_pago,
            "descuento": descuento,
            "detalles": [{"producto": producto_id, "cantidad": cantidad}],
        }

        serializer = VentaCreateSerializer(data=payload, context={"request": request})
        if not serializer.is_valid():
            messages.error(request, "No se pudo registrar la venta. Revisa caja, producto, cantidad y stock.")
            return redirect("ventas:nueva_venta")

        try:
            with transaction.atomic():
                data = serializer.validated_data
                venta = Venta.objects.create(
                    cajero=request.user,
                    caja=data["caja"],
                    metodo_pago=data["metodo_pago"],
                    descuento=data["descuento"],
                )

                for item in data["detalles"]:
                    producto = item["producto"]
                    cantidad_item = item["cantidad"]
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=cantidad_item,
                        precio_unitario=Decimal(str(item["precio_unitario"])),
                        descuento_linea=Decimal(str(item["descuento_linea"])),
                    )
                    producto.stock_actual -= cantidad_item
                    producto.save(update_fields=["stock_actual"])

                venta.calcular_totales()
                MovimientoCaja.objects.create(
                    caja=venta.caja,
                    tipo="INGRESO",
                    monto=venta.total,
                    concepto=f"Venta #{venta.id}",
                    usuario=request.user,
                )
        except Exception:
            messages.error(request, "Ocurrió un error al registrar la venta. No se guardaron cambios parciales.")
            return redirect("ventas:nueva_venta")

        messages.success(request, f"Venta #{venta.id} registrada correctamente.")
        return redirect("ventas:dashboard")


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
            "es_admin": request.user.rol == "admin",
        }
        return render(request, "dashboard/caja.html", context)


@method_decorator(login_required, name="dispatch")
class CajaAccionView(View):
    def post(self, request, pk, accion):
        caja = get_object_or_404(Caja, pk=pk)
        es_admin = request.user.rol == "admin"
        es_dueno = caja.cajero_id == request.user.id

        if not es_admin and not es_dueno:
            messages.error(request, "No puedes operar una caja de otro cajero.")
            return redirect("ventas:caja_dashboard")

        if accion == "abrir":
            if caja.estado == "ABIERTA":
                messages.warning(request, "La caja ya estÃ¡ ABIERTA.")
                return redirect("ventas:caja_dashboard")
            if Caja.objects.filter(cajero=caja.cajero, estado="ABIERTA").exclude(pk=caja.pk).exists():
                messages.error(request, "Ese cajero ya tiene otra caja ABIERTA.")
                return redirect("ventas:caja_dashboard")

            saldo_inicial = request.POST.get("saldo_inicial", "0")
            caja.saldo_inicial = Decimal(str(saldo_inicial))
            caja.saldo_final = None
            caja.fecha_apertura = timezone.now()
            caja.fecha_cierre = None
            caja.estado = "ABIERTA"
            caja.save(update_fields=["saldo_inicial", "saldo_final", "fecha_apertura", "fecha_cierre", "estado"])
            messages.success(request, f"Se abriÃ³ la caja {caja.nombre}.")
            return redirect("ventas:caja_dashboard")

        if accion == "cerrar":
            if caja.estado != "ABIERTA":
                messages.warning(request, "Solo puedes cerrar una caja ABIERTA.")
                return redirect("ventas:caja_dashboard")

            caja.saldo_final = caja.saldo_actual
            caja.fecha_cierre = timezone.now()
            caja.estado = "CERRADA"
            caja.save(update_fields=["saldo_final", "fecha_cierre", "estado"])
            messages.success(request, f"Se cerrÃ³ la caja {caja.nombre}.")
            return redirect("ventas:caja_dashboard")

        messages.error(request, "AcciÃ³n no vÃ¡lida.")
        return redirect("ventas:caja_dashboard")

@method_decorator(login_required, name="dispatch")
class CajaAbrirNuevaView(View):
    def post(self, request):
        if Caja.objects.filter(cajero=request.user, estado="ABIERTA").exists():
            messages.warning(request, "Ya tienes una caja ABIERTA.")
            return redirect("ventas:caja_dashboard")

        saldo_inicial = Decimal(str(request.POST.get("saldo_inicial", "0") or "0"))
        nombre = request.POST.get("nombre", "").strip() or f"Caja {request.user.username}"

        caja = Caja.objects.create(
            nombre=nombre,
            saldo_inicial=saldo_inicial,
            cajero=request.user,
            estado="ABIERTA",
        )
        messages.success(request, f"Se abrio la caja {caja.nombre}.")
        return redirect("ventas:caja_dashboard")

