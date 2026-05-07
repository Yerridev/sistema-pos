from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdmin(BasePermission):
    """Solo admin puede acceder."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.rol == 'admin'
        )


class IsAdminOrReadOnly(BasePermission):
    """Admin puede escribir; cajero solo lee."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.rol == 'admin'
