from decimal import Decimal

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.exceptions import AccesoNoAutorizado, ReglaNegocioViolada
from .models import Caja
from .permissions import CanAccessCaja
from .serializers import CajaSerializer
from .services import CajaService


class CajaViewSet(viewsets.ModelViewSet):
    serializer_class = CajaSerializer
    permission_classes = [CanAccessCaja]

    def get_queryset(self):
        queryset = Caja.objects.select_related('cajero')
        if self.request.user.rol == 'admin':
            return queryset.all()
        return queryset.filter(cajero=self.request.user)

    @action(detail=True, methods=['post'])
    def abrir(self, request, pk=None):
        caja = self.get_object()
        saldo_inicial = Decimal(str(request.data.get('saldo_inicial', caja.saldo_inicial or 0)))
        try:
            caja = CajaService.abrir_caja_existente(caja, request.user, saldo_inicial)
        except ReglaNegocioViolada as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except AccesoNoAutorizado as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(self.get_serializer(caja).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='apertura')
    def apertura(self, request, pk=None):
        return self.abrir(request, pk=pk)

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        caja = self.get_object()
        try:
            caja = CajaService.cerrar(caja, request.user)
        except ReglaNegocioViolada as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except AccesoNoAutorizado as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(self.get_serializer(caja).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='cierre')
    def cierre(self, request, pk=None):
        return self.cerrar(request, pk=pk)
