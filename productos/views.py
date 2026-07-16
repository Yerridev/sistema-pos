import json
from django.db import models
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from urllib.parse import urlencode

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.exceptions import AppError
from .models import Categoria, Producto
from .permissions import IsAdminOrReadOnly
from .serializers import CategoriaSerializer, ProductoListSerializer, ProductoSerializer
from .services import CategoriaService, ProductoService
from .utils import get_role_permissions


# ─── API ViewSets ─────────────────────────────────────────────────────────────

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
    ordering_fields = ['nombre', 'creado_en']
    ordering = ['nombre']

    @extend_schema(
        summary="Listar categorías",
        description="Retorna lista de categorías. Solo admin puede crear/editar.",
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
    ordering_fields = ['nombre', 'precio_venta', 'stock_actual', 'creado_en']
    ordering = ['nombre']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductoListSerializer
        return ProductoSerializer

    @extend_schema(summary="Listar productos", tags=['Productos'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Crear producto", tags=['Productos'])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary="Obtener detalle de producto", tags=['Productos'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def buscar(self, request):
        q = request.GET.get('q', '').strip()
        queryset = self.get_queryset().filter(activo=True)
        if q:
            queryset = queryset.filter(
                models.Q(nombre__icontains=q) | models.Q(codigo_barra__icontains=q)
            )
        serializer = ProductoListSerializer(queryset[:20], many=True, context=self.get_serializer_context())
        return Response(serializer.data)


# ─── Dashboard Template Views ─────────────────────────────────────────────────

def _build_queryset(request):
    """Construye y filtra el queryset base de productos según parámetros GET."""
    search = request.GET.get('search', '').strip() or None
    categoria = request.GET.get('categoria', '').strip() or None
    stock_status = request.GET.get('stock_status', '').strip() or None

    qs = Producto.objects.select_related('categoria').filter(activo=True)

    if search:
        qs = qs.filter(
            models.Q(nombre__icontains=search) | models.Q(codigo_barra__icontains=search)
        )
    if categoria:
        qs = qs.filter(categoria_id=categoria)
    if stock_status == 'critico':
        qs = qs.filter(stock_actual__lt=models.F('stock_minimo'))
    elif stock_status == 'bajo':
        qs = qs.filter(
            stock_actual__gte=models.F('stock_minimo'),
            stock_actual__lte=models.F('stock_minimo') * 2,
        )
    elif stock_status == 'normal':
        qs = qs.filter(stock_actual__gt=models.F('stock_minimo') * 2)

    return qs, {'search': search or '', 'categoria': categoria or '', 'stock_status': stock_status or ''}


def _build_stats(qs):
    """Calcula estadísticas del queryset."""
    from collections import Counter
    total = qs.count()
    criticos = qs.filter(stock_actual__lt=models.F('stock_minimo')).count()
    valor = sum(p.precio_venta * p.stock_actual for p in qs)
    cats = Counter(qs.values_list('categoria__nombre', flat=True))
    top_cat = cats.most_common(1)[0][0] if cats else 'N/A'
    return [
        {'label': 'Total productos', 'value': total,            'icon': 'inventory_2', 'warning': False},
        {'label': 'Stock crítico',   'value': criticos,         'icon': 'warning',     'warning': True},
        {'label': 'Valor inventario','value': f"S/. {valor:.2f}",'icon': 'savings',    'warning': False},
        {'label': 'Categoría top',   'value': top_cat,          'icon': 'category',    'warning': False},
    ]


@method_decorator(login_required, name='dispatch')
class InventarioDashboardView(View):

    def get(self, request):
        page = int(request.GET.get('page', 1))
        qs, filters_ctx = _build_queryset(request)

        paginator = Paginator(qs, 20)
        page_obj = paginator.get_page(page)
        products = list(page_obj.object_list)

        pagination_query = urlencode({k: v for k, v in filters_ctx.items() if v})
        permissions = get_role_permissions(getattr(request.user, 'rol', None))
        categories = list(Categoria.objects.filter(activo=True).order_by('nombre'))

        context = {
            'stats_list': _build_stats(qs),
            'products': products,
            'page_obj': page_obj,
            'filters': {**filters_ctx, 'page': page},
            'can_edit': permissions['can_edit'],
            'can_delete': permissions['can_delete'],
            'categories': categories,
            'categories_json': json.dumps([{'id': c.id, 'nombre': c.nombre} for c in categories]),
            'pagination_query': pagination_query,
            'total_count': paginator.count,
            'page_title': 'Inventario',
            'active_nav': 'productos:dashboard',
        }
        return render(request, 'dashboard/inventory.html', context)


@method_decorator(login_required, name='dispatch')
class ProductoCreateView(View):
    """Crea un producto vía POST (usado por el modal AJAX)."""

    def post(self, request):
        if not get_role_permissions(getattr(request.user, 'rol', None))['can_edit']:
            return JsonResponse({'error': 'Sin permisos para crear productos.'}, status=403)

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = request.POST.dict()

        try:
            producto = ProductoService.crear(data)
        except AppError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        return JsonResponse({
            'success': True,
            'id': producto.id,
            'nombre': producto.nombre,
            'message': f'Producto "{producto.nombre}" creado correctamente.',
        }, status=201)


@method_decorator(login_required, name='dispatch')
class ProductoUpdateView(View):
    """Actualiza un producto vía POST/PUT (usado por el modal AJAX)."""

    def get(self, request, pk):
        """Devuelve datos del producto en JSON para pre-llenar el modal."""
        producto = get_object_or_404(Producto, pk=pk)
        return JsonResponse({
            'id': producto.id,
            'nombre': producto.nombre,
            'codigo_barra': producto.codigo_barra or '',
            'categoria': producto.categoria_id,
            'descripcion': producto.descripcion or '',
            'precio_venta': str(producto.precio_venta),
            'costo': str(producto.costo),
            'stock_actual': producto.stock_actual,
            'stock_minimo': producto.stock_minimo,
            'unidad': producto.unidad,
            'activo': producto.activo,
        })

    def post(self, request, pk):
        if not get_role_permissions(getattr(request.user, 'rol', None))['can_edit']:
            return JsonResponse({'error': 'Sin permisos para editar productos.'}, status=403)

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = request.POST.dict()

        producto = get_object_or_404(Producto, pk=pk)
        try:
            ProductoService.actualizar(producto, data)
        except AppError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        return JsonResponse({
            'success': True,
            'message': f'Producto "{producto.nombre}" actualizado correctamente.',
        })


@method_decorator(login_required, name='dispatch')
class ProductoDeleteView(View):
    """Elimina (desactiva) un producto vía POST."""

    def post(self, request, pk):
        if not get_role_permissions(getattr(request.user, 'rol', None))['can_delete']:
            return JsonResponse({'error': 'Sin permisos para eliminar productos.'}, status=403)

        producto = get_object_or_404(Producto, pk=pk)
        nombre = producto.nombre
        ProductoService.eliminar(producto)
        return JsonResponse({'success': True, 'message': f'Producto "{nombre}" eliminado.'})


@method_decorator(login_required, name='dispatch')
class CategoriaListView(View):
    """Lista categorías en JSON (para selects dinámicos)."""

    def get(self, request):
        cats = list(Categoria.objects.filter(activo=True).order_by('nombre').values('id', 'nombre', 'descripcion'))
        return JsonResponse({'results': cats})


@method_decorator(login_required, name='dispatch')
class CategoriaCreateView(View):
    """Crea una categoria desde el dashboard."""

    def post(self, request):
        if not get_role_permissions(getattr(request.user, 'rol', None))['can_edit']:
            return JsonResponse({'error': 'Sin permisos para crear categorias.'}, status=403)

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = request.POST.dict()

        nombre = data.get('nombre', '').strip()
        descripcion = data.get('descripcion', '').strip()
        try:
            categoria = CategoriaService.crear(nombre, descripcion)
        except AppError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        return JsonResponse({
            'success': True,
            'id': categoria.id,
            'nombre': categoria.nombre,
            'descripcion': categoria.descripcion or '',
            'message': f'Categoria "{categoria.nombre}" creada correctamente.',
        }, status=201)


@method_decorator(login_required, name='dispatch')
class CategoriaUpdateView(View):
    """Edita una categoria desde el dashboard."""

    def get(self, request, pk):
        categoria = get_object_or_404(Categoria, pk=pk)
        return JsonResponse({
            'id': categoria.id,
            'nombre': categoria.nombre,
            'descripcion': categoria.descripcion or '',
            'activo': categoria.activo,
        })

    def post(self, request, pk):
        if not get_role_permissions(getattr(request.user, 'rol', None))['can_edit']:
            return JsonResponse({'error': 'Sin permisos para editar categorias.'}, status=403)

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = request.POST.dict()

        categoria = get_object_or_404(Categoria, pk=pk)
        try:
            CategoriaService.actualizar(categoria, data.get('nombre', '').strip(), data.get('descripcion', '').strip())
        except AppError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        return JsonResponse({
            'success': True,
            'message': f'Categoria "{categoria.nombre}" actualizada correctamente.',
        })


@method_decorator(login_required, name='dispatch')
class CategoriaDeleteView(View):
    """Desactiva una categoria si no tiene productos activos."""

    def post(self, request, pk):
        if not get_role_permissions(getattr(request.user, 'rol', None))['can_delete']:
            return JsonResponse({'error': 'Sin permisos para eliminar categorias.'}, status=403)

        categoria = get_object_or_404(Categoria, pk=pk)
        try:
            CategoriaService.eliminar(categoria)
        except AppError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        return JsonResponse({'success': True, 'message': f'Categoria "{categoria.nombre}" eliminada.'})
