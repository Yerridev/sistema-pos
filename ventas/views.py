from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from caja.models import Caja, MovimientoCaja
from productos.models import Producto
from .models import DetalleVenta, Venta
from .permissions import CanAccessVentaObject, CanAnularVenta, IsCajeroOrAdmin


class VentaFallbackSerializer(serializers.Serializer):
    """Serializer minimo para que el ViewSet pueda cargar antes del merge final."""


class VentaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsCajeroOrAdmin, CanAccessVentaObject, CanAnularVenta]

    def get_serializer_class(self):
        try:
            from .serializers import VentaCreateSerializer, VentaDetalleSerializer, VentaSerializer
        except ImportError:
            return VentaFallbackSerializer

        if self.action == "create":
            return VentaCreateSerializer
        if self.action in ["retrieve", "anular"]:
            return VentaDetalleSerializer
        return VentaSerializer

    def get_queryset(self):
        queryset = Venta.objects.select_related("cajero", "caja").prefetch_related("detalles")

        if self.request.user.rol == "admin":
            return queryset.all()
        return queryset.filter(cajero=self.request.user)

    def _serialize_response(self, venta):
        serializer_class = self.get_serializer_class()
        if self.action == "create":
            from .serializers import VentaDetalleSerializer

            serializer_class = VentaDetalleSerializer
        if serializer_class is VentaFallbackSerializer:
            return {
                "id": venta.id,
                "fecha": venta.fecha,
                "cajero": venta.cajero_id,
                "caja": venta.caja_id,
                "subtotal": venta.subtotal,
                "descuento": venta.descuento,
                "igv": venta.igv,
                "total": venta.total,
                "metodo_pago": venta.metodo_pago,
                "estado": venta.estado,
            }
        return serializer_class(venta, context=self.get_serializer_context()).data

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        caja = data.get("caja")
        caja_id = data.get("caja_id") or getattr(caja, "id", caja)
        detalles = data.get("detalles", [])
        metodo_pago = data.get("metodo_pago", "EFECTIVO")
        descuento = Decimal(str(data.get("descuento", 0)))

        try:
            caja = Caja.objects.select_for_update().get(pk=caja_id)
        except Caja.DoesNotExist:
            return Response({"caja_id": "La caja no existe."}, status=status.HTTP_400_BAD_REQUEST)

        if caja.estado != "ABIERTA":
            return Response(
                {"caja_id": "La caja debe estar ABIERTA para registrar ventas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if caja.cajero_id != request.user.id and request.user.rol != "admin":
            return Response(
                {"detail": "No puede vender en una caja de otro cajero."},
                status=status.HTTP_403_FORBIDDEN,
            )

        venta = Venta.objects.create(
            cajero=request.user,
            caja=caja,
            metodo_pago=metodo_pago,
            descuento=descuento,
        )

        for item in detalles:
            producto = item.get("producto")
            producto_id = getattr(producto, "id", producto)
            cantidad = int(item.get("cantidad", 0))
            descuento_linea = Decimal(str(item.get("descuento_linea", 0)))

            if cantidad <= 0:
                transaction.set_rollback(True)
                return Response({"cantidad": "La cantidad debe ser mayor que cero."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                producto = Producto.objects.select_for_update().get(pk=producto_id, activo=True)
            except Producto.DoesNotExist:
                transaction.set_rollback(True)
                return Response({"producto": f"El producto {producto_id} no existe."}, status=status.HTTP_400_BAD_REQUEST)

            if producto.stock_actual < cantidad:
                transaction.set_rollback(True)
                return Response(
                    {"stock": f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock_actual}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            precio_unitario = Decimal(str(item.get("precio_unitario") or producto.precio_venta))
            if descuento_linea > precio_unitario * cantidad:
                transaction.set_rollback(True)
                return Response(
                    {"descuento_linea": "El descuento de linea no puede superar el subtotal de la linea."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                descuento_linea=descuento_linea,
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

        return Response(self._serialize_response(venta), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def anular(self, request, pk=None):
        venta = self.get_object()
        motivo = request.data.get("motivo") or request.data.get("motivo_anulacion")
        restaurar_stock = request.data.get("restaurar_stock", True)

        if not motivo:
            return Response({"motivo": "El motivo de anulacion es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        if venta.estado == "ANULADA":
            return Response({"detail": "La venta ya esta anulada."}, status=status.HTTP_400_BAD_REQUEST)
        if venta.cajero_id != request.user.id and request.user.rol != "admin":
            return Response({"detail": "No tiene permiso para anular esta venta."}, status=status.HTTP_403_FORBIDDEN)

        venta.estado = "ANULADA"
        venta.motivo_anulacion = motivo
        venta.anulado_por = request.user
        venta.fecha_anulacion = timezone.now()
        venta.save(update_fields=["estado", "motivo_anulacion", "anulado_por", "fecha_anulacion"])

        if restaurar_stock:
            for detalle in DetalleVenta.objects.select_related("producto").filter(venta=venta):
                detalle.producto.stock_actual += detalle.cantidad
                detalle.producto.save(update_fields=["stock_actual"])

        MovimientoCaja.objects.create(
            caja=venta.caja,
            tipo="EGRESO",
            monto=venta.total,
            concepto=f"Anulacion venta #{venta.id}: {motivo}",
            usuario=request.user,
        )

        return Response(self._serialize_response(venta), status=status.HTTP_200_OK)
