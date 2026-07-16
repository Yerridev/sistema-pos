from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """Permite acceso solo a usuarios autenticados con rol admin."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "rol", None) == "admin"
        )
