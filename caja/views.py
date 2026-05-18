from decimal import Decimal

from django.apps import apps
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class CajaFallbackSerializer(serializers.Serializer):
    """Serializer mínimo para que el ViewSet pueda cargar antes del merge final."""


class CajaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def _model(self):
        return apps.get_model('caja', 'Caja')

    def get_serializer_class(self):
        try:
            from .serializers import CajaSerializer
        except ImportError:
            return CajaFallbackSerializer
        return CajaSerializer

    def get_queryset(self):
        Caja = self._model()
        queryset = Caja.objects.select_related('cajero')

        if self.request.user.rol == 'admin':
            return queryset.all()
        return queryset.filter(cajero=self.request.user)

    def _serialize_response(self, caja):
        serializer_class = self.get_serializer_class()
        if serializer_class is CajaFallbackSerializer:
            return {
                'id': caja.id,
                'nombre': caja.nombre,
                'saldo_inicial': caja.saldo_inicial,
                'saldo_actual': caja.saldo_actual,
                'saldo_final': caja.saldo_final,
                'estado': caja.estado,
                'cajero': caja.cajero_id,
                'fecha_apertura': caja.fecha_apertura,
                'fecha_cierre': caja.fecha_cierre,
            }
        return serializer_class(caja, context=self.get_serializer_context()).data

    @action(detail=True, methods=['post'])
    def abrir(self, request, pk=None):
        Caja = self._model()
        caja = self.get_object()

        if Caja.objects.filter(cajero=request.user, estado='ABIERTA').exclude(pk=caja.pk).exists():
            return Response({'detail': 'Ya existe una caja ABIERTA para este cajero.'}, status=status.HTTP_400_BAD_REQUEST)
        if caja.estado == 'ABIERTA':
            return Response({'detail': 'La caja ya está ABIERTA.'}, status=status.HTTP_400_BAD_REQUEST)

        caja.saldo_inicial = Decimal(str(request.data.get('saldo_inicial', caja.saldo_inicial or 0)))
        caja.fecha_apertura = timezone.now()
        caja.fecha_cierre = None
        caja.saldo_final = None
        caja.estado = 'ABIERTA'
        caja.cajero = request.user
        caja.save(update_fields=['saldo_inicial', 'fecha_apertura', 'fecha_cierre', 'saldo_final', 'estado', 'cajero'])

        return Response(self._serialize_response(caja), status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        caja = self.get_object()

        if caja.estado != 'ABIERTA':
            return Response({'detail': 'Solo se puede cerrar una caja ABIERTA.'}, status=status.HTTP_400_BAD_REQUEST)
        if caja.cajero_id != request.user.id and request.user.rol != 'admin':
            return Response({'detail': 'No puede cerrar una caja de otro cajero.'}, status=status.HTTP_403_FORBIDDEN)

        caja.saldo_final = caja.saldo_actual
        caja.fecha_cierre = timezone.now()
        caja.estado = 'CERRADA'
        caja.save(update_fields=['saldo_final', 'fecha_cierre', 'estado'])

        return Response(self._serialize_response(caja), status=status.HTTP_200_OK)
