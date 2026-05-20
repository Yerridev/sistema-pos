from rest_framework.permissions import BasePermission


class IsCajeroOrAdmin(BasePermission):
    """Permite acceso solo a usuarios autenticados con rol cajero o admin."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "rol", None) in {"admin", "cajero"}
        )


class CanAccessVentaObject(BasePermission):
    """Admin ve todo; cajero solo sus ventas."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "rol", None) == "admin":
            return True
        return obj.cajero_id == user.id


class CanAnularVenta(BasePermission):
    """Solo admin o el cajero dueño de la venta puede anular."""

    def has_object_permission(self, request, view, obj):
        if getattr(view, "action", None) != "anular":
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "rol", None) == "admin":
            return True
        return obj.cajero_id == user.id
