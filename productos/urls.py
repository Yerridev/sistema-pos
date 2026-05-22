from django.urls import path

from .views import (
    InventarioDashboardView,
    ProductoCreateView,
    ProductoUpdateView,
    ProductoDeleteView,
    CategoriaListView,
)

app_name = 'productos'

urlpatterns = [
    path('dashboard/inventario/', InventarioDashboardView.as_view(), name='dashboard'),
    path('dashboard/inventario/crear/', ProductoCreateView.as_view(), name='producto_crear'),
    path('dashboard/inventario/<int:pk>/editar/', ProductoUpdateView.as_view(), name='producto_editar'),
    path('dashboard/inventario/<int:pk>/eliminar/', ProductoDeleteView.as_view(), name='producto_eliminar'),
    path('dashboard/categorias/', CategoriaListView.as_view(), name='categorias'),
]
