from django.urls import path

from .views import (
    InventarioDashboardView,
    ProductoCreateView,
    ProductoUpdateView,
    ProductoDeleteView,
    CategoriaListView,
    CategoriaCreateView,
    CategoriaUpdateView,
    CategoriaDeleteView,
)

app_name = 'productos'

urlpatterns = [
    path('dashboard/inventario/', InventarioDashboardView.as_view(), name='dashboard'),
    path('dashboard/inventario/crear/', ProductoCreateView.as_view(), name='producto_crear'),
    path('dashboard/inventario/<int:pk>/editar/', ProductoUpdateView.as_view(), name='producto_editar'),
    path('dashboard/inventario/<int:pk>/eliminar/', ProductoDeleteView.as_view(), name='producto_eliminar'),
    path('dashboard/categorias/', CategoriaListView.as_view(), name='categorias'),
    path('dashboard/categorias/crear/', CategoriaCreateView.as_view(), name='categoria_crear'),
    path('dashboard/categorias/<int:pk>/editar/', CategoriaUpdateView.as_view(), name='categoria_editar'),
    path('dashboard/categorias/<int:pk>/eliminar/', CategoriaDeleteView.as_view(), name='categoria_eliminar'),
]
