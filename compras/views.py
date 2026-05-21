from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from productos.models import Producto
from productos.permissions import IsAdmin
from .models import Compra, DetalleCompra, Proveedor
from .serializers import CompraReadSerializer, CompraSerializer, ProveedorSerializer


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
    }
    return render(request, "dashboard/compras.html", context)


@login_required
@user_passes_test(_is_admin)
@require_POST
@transaction.atomic
def registrar_compra(request):
    proveedor_id = request.POST.get("proveedor")
    producto_id = request.POST.get("producto")
    cantidad = request.POST.get("cantidad", "").strip()
    costo_unitario = request.POST.get("costo_unitario", "").strip()

    try:
        proveedor = Proveedor.objects.get(pk=proveedor_id, activo=True)
    except Proveedor.DoesNotExist:
        messages.error(request, "Selecciona un proveedor valido.")
        return redirect("compras:dashboard")

    try:
        producto = Producto.objects.select_for_update().get(pk=producto_id, activo=True)
    except Producto.DoesNotExist:
        messages.error(request, "Selecciona un producto valido.")
        return redirect("compras:dashboard")

    try:
        cantidad = int(cantidad)
        if cantidad <= 0:
            raise ValueError
    except ValueError:
        messages.error(request, "La cantidad debe ser mayor que cero.")
        return redirect("compras:dashboard")

    try:
        from decimal import Decimal
        costo_unitario = Decimal(costo_unitario)
        if costo_unitario < 0:
            raise ValueError
    except Exception:
        messages.error(request, "El costo unitario debe ser un numero valido.")
        return redirect("compras:dashboard")

    compra = Compra.objects.create(proveedor=proveedor)
    DetalleCompra.objects.create(
        compra=compra,
        producto=producto,
        cantidad=cantidad,
        costo_unitario=costo_unitario,
    )
    producto.stock_actual += cantidad
    producto.costo = costo_unitario
    producto.save(update_fields=["stock_actual", "costo"])
    compra.calcular_total()

    messages.success(request, f"Compra #{compra.id} registrada. Stock actualizado para {producto.nombre}.")
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
