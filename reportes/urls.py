from django.urls import path

from .views import reportes_dashboard

app_name = "reportes"

urlpatterns = [
    path("dashboard/reportes/", reportes_dashboard, name="dashboard"),
]
