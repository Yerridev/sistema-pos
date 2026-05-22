from django.urls import path

from .dashboard_views import CajaDashboardView, NuevaVentaView, VentaDashboardView


app_name = "ventas"

urlpatterns = [
    path("dashboard/ventas/", VentaDashboardView.as_view(), name="dashboard"),
    path("dashboard/ventas/nueva/", NuevaVentaView.as_view(), name="nueva_venta"),
    path("dashboard/caja/", CajaDashboardView.as_view(), name="caja_dashboard"),
]
