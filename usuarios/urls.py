from django.urls import path

from .views import (
    UsuarioListView,
    UsuarioCreateView,
    UsuarioDetailView,
    UsuarioUpdateView,
    UsuarioStatusView,
    UsuarioResetPasswordView,
)

app_name = "usuarios"

urlpatterns = [
    path("dashboard/usuarios/", UsuarioListView.as_view(), name="list"),
    path("dashboard/usuarios/crear/", UsuarioCreateView.as_view(), name="create"),
    path("dashboard/usuarios/<int:pk>/", UsuarioDetailView.as_view(), name="detail"),
    path("dashboard/usuarios/<int:pk>/editar/", UsuarioUpdateView.as_view(), name="update"),
    path("dashboard/usuarios/<int:pk>/estado/", UsuarioStatusView.as_view(), name="status"),
    path("dashboard/usuarios/<int:pk>/password/", UsuarioResetPasswordView.as_view(), name="password"),
]
