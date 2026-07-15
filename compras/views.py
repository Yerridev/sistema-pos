from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from decimal import Decimal, InvalidOperation

from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.exceptions import AppError, RecursoNoEncontrado, ReglaNegocioViolada
from productos.permissions import IsAdmin
from productos.models import Producto
from .models import Compra, Proveedor
from .serializers import CompraReadSerializer, CompraSerializer, ProveedorSerializer
from .services import CompraService


class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class CompraViewSet(viewsets.ModelViewSet):
    queryset = Compra.objects.select_related("proveedor").prefetch_related("detalles__producto")
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return CompraSerializer
        return CompraReadSerializer


def _is_admin(user):
    return bool(user and user.is_authenticated and getattr(user, "rol", None) == "admin")


@login_required
@user_passes_test(_is_admin)
def compras_dashboard(request):
    context = {
        "proveedores": Proveedor.objects.filter(activo=True).order_by("nombre"),
        "productos": Producto.objects.select_related("categoria").filter(activo=True).order_by("nombre"),
        "compras": Compra.objects.select_related("proveedor").prefetch_related("detalles__producto")[:10],
        "page_title": "Compras",
        "active_nav": "compras:dashboard",
    }
    return render(request, "dashboard/compras.html", context)


@login_required
@user_passes_test(_is_admin)
@require_POST
def registrar_compra(request):
    try:
        proveedor = Proveedor.objects.get(pk=request.POST.get("proveedor"), activo=True)
        detalles = [{
            "producto": int(request.POST.get("producto")),
            "cantidad": int(request.POST.get("cantidad")),
            "costo_unitario": Decimal(request.POST.get("costo_unitario", "").strip()),
        }]
        compra = CompraService.registrar(proveedor=proveedor, detalles=detalles)
        messages.success(request, f"Compra #{compra.id} registrada correctamente.")
    except (Proveedor.DoesNotExist, ValueError, InvalidOperation, AppError) as exc:
        messages.error(request, str(exc))
    return redirect("compras:dashboard")


@login_required
@user_passes_test(_is_admin)
@require_POST
def crear_proveedor(request):
    nombre = request.POST.get("nombre", "").strip()
    ruc = request.POST.get("ruc", "").strip()
    contacto = request.POST.get("contacto", "").strip()

    if not nombre or not ruc:
        messages.error(request, "Nombre y RUC son obligatorios.")
        return redirect("compras:dashboard")
    if Proveedor.objects.filter(ruc=ruc).exists():
        messages.error(request, "Ya existe un proveedor con ese RUC.")
        return redirect("compras:dashboard")

    Proveedor.objects.create(nombre=nombre, ruc=ruc, contacto=contacto)
    messages.success(request, "Proveedor registrado correctamente.")
    return redirect("compras:dashboard")
