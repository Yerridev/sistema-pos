from django.urls import path

from .dashboard_views import CajaAbrirNuevaView, CajaAccionView, CajaDashboardView, NuevaVentaView, VentaDashboardView


app_name = "ventas"

urlpatterns = [
    path("dashboard/ventas/", VentaDashboardView.as_view(), name="dashboard"),
    path("dashboard/ventas/nueva/", NuevaVentaView.as_view(), name="nueva_venta"),
    path("dashboard/caja/", CajaDashboardView.as_view(), name="caja_dashboard"),
    path("dashboard/caja/abrir/", CajaAbrirNuevaView.as_view(), name="caja_abrir_nueva"),
    path("dashboard/caja/<int:pk>/<str:accion>/", CajaAccionView.as_view(), name="caja_accion"),
]
