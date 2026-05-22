from django.urls import path

from .dashboard_views import (
    CajaDashboardView,
    NuevaVentaView,
    VentaDetalleDashboardView,
    VentaDashboardView,
    abrir_caja,
    anular_venta_dashboard,
    buscar_productos_venta,
    cerrar_caja,
    registrar_movimiento_caja,
)


app_name = "ventas"

urlpatterns = [
    path("dashboard/ventas/", VentaDashboardView.as_view(), name="dashboard"),
    path("dashboard/ventas/nueva/", NuevaVentaView.as_view(), name="nueva_venta"),
    path("dashboard/ventas/buscar-productos/", buscar_productos_venta, name="buscar_productos"),
    path("dashboard/ventas/<int:pk>/", VentaDetalleDashboardView.as_view(), name="detalle_venta"),
    path("dashboard/ventas/<int:pk>/anular/", anular_venta_dashboard, name="anular_venta"),
    path("dashboard/caja/", CajaDashboardView.as_view(), name="caja_dashboard"),
    path("dashboard/caja/abrir/", abrir_caja, name="abrir_caja"),
    path("dashboard/caja/<int:pk>/cerrar/", cerrar_caja, name="cerrar_caja"),
    path("dashboard/caja/<int:pk>/movimiento/", registrar_movimiento_caja, name="movimiento_caja"),
]
