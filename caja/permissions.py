from rest_framework.permissions import BasePermission


class CanAccessCaja(BasePermission):
    """Admin ve todas las cajas; cajero solo las suyas."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "rol", None) in {"admin", "cajero"}
        )

    def has_object_permission(self, request, view, obj):
        method = getattr(request, "method", "GET")
        if method.upper() not in {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"}:
            return False
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "rol", None) == "admin":
            return True
        return obj.cajero_id == user.id
