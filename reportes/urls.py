from django.urls import path

from .views import reportes_dashboard, admin_dashboard

app_name = "reportes"

urlpatterns = [
    path("dashboard/reportes/", reportes_dashboard, name="dashboard"),
    path("dashboard/admin/", admin_dashboard, name="admin_dashboard"),
]
