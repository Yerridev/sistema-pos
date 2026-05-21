from django.urls import path

from .views import compras_dashboard, crear_proveedor, registrar_compra

app_name = "compras"

urlpatterns = [
    path("dashboard/compras/", compras_dashboard, name="dashboard"),
    path("dashboard/compras/registrar/", registrar_compra, name="registrar"),
    path("dashboard/compras/proveedores/crear/", crear_proveedor, name="proveedor_crear"),
]
