from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from .models import Categoria, Producto
from .serializers import CategoriaSerializer, ProductoSerializer, ProductoListSerializer
from .permissions import IsAdminOrReadOnly


class CategoriaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar categorías de productos.
    - Admin: CRUD completo
    - Cajero: Solo lectura
    """
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'descripcion']
    ordering_fields = ['nombre', 'created_at']
    ordering = ['nombre']

    @extend_schema(
        summary="Listar categorías",
        description="Retorna lista de categorías de productos. Solo admin puede crear/editar.",
        tags=['Categorías'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ProductoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar productos.
    - Admin: CRUD completo
    - Cajero/Otros: Solo lectura
    """
    queryset = Producto.objects.select_related('categoria').all()
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categoria', 'activo']
    search_fields = ['codigo_barra', 'nombre', 'categoria__nombre']
    ordering_fields = ['nombre', 'precio_venta', 'stock_actual', 'created_at']
    ordering = ['nombre']

    def get_serializer_class(self):
        """Usa serializer simplificado para listas."""
        if self.action == 'list':
            return ProductoListSerializer
        return ProductoSerializer

    @extend_schema(
        summary="Listar productos",
        description="Retorna lista de productos con opción de filtrar por categoría, stock crítico, etc.",
        tags=['Productos'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Crear producto",
        description="Solo admin. Valida que precio_venta > costo.",
        tags=['Productos'],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Obtener detalle de producto",
        description="Retorna información completa del producto incluyendo ganancia unitaria.",
        tags=['Productos'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
