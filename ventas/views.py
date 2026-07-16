from decimal import Decimal

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from core.exceptions import AccesoNoAutorizado, AppError, RecursoNoEncontrado, ReglaNegocioViolada
from .models import Venta
from .permissions import CanAccessVentaObject, CanAnularVenta, IsCajeroOrAdmin
from .serializers import VentaCreateSerializer, VentaDetalleSerializer, VentaSerializer
from .services import VentaService


class VentaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsCajeroOrAdmin, CanAccessVentaObject, CanAnularVenta]

    def get_serializer_class(self):
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
        serializer_class = VentaDetalleSerializer if self.action == "create" else self.get_serializer_class()
        return serializer_class(venta, context=self.get_serializer_context()).data

    def _domain_error_response(self, exc):
        if isinstance(exc, ReglaNegocioViolada):
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if isinstance(exc, AccesoNoAutorizado):
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        if isinstance(exc, RecursoNoEncontrado):
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        raise exc

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            venta = VentaService.registrar(
                usuario=request.user,
                caja_id=data.get("caja_id") or data.get("caja"),
                metodo_pago=data.get("metodo_pago", "EFECTIVO"),
                descuento=data.get("descuento", Decimal("0.00")),
                detalles=data.get("detalles", []),
            )
        except (ReglaNegocioViolada, AccesoNoAutorizado, RecursoNoEncontrado) as exc:
            return self._domain_error_response(exc)

        return Response(self._serialize_response(venta), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="politicas-descuento")
    def politicas_descuento(self, request):
        """Lista las políticas de descuento disponibles (Strategy Pattern)."""
        from core.descuentos import POLITICAS, POLITICAS_LABELS
        return Response({
            "politicas": [
                {"key": key, "label": POLITICAS_LABELS.get(key, key)}
                for key in POLITICAS
            ]
        })

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        venta = self.get_object()
        motivo = request.data.get("motivo") or request.data.get("motivo_anulacion")
        if not motivo:
            return Response({"motivo": "El motivo de anulacion es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)

        restaurar_stock = request.data.get("restaurar_stock", True)
        try:
            venta = VentaService.anular(venta, request.user, motivo, restaurar_stock=restaurar_stock)
        except ReglaNegocioViolada as exc:
            return self._domain_error_response(exc)

        return Response(self._serialize_response(venta), status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """Bloquea la eliminación física de ventas."""
        raise MethodNotAllowed("DELETE", detail="Las ventas no se pueden eliminar. Use POST /anular/.")
