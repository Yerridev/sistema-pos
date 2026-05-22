from collections import Counter
from decimal import Decimal


def get_role_permissions(role):
    """Retorna dict de permisos según el rol del usuario (admin | cajero)."""
    can_edit   = role == 'admin'
    can_delete = role == 'admin'
    return {
        'can_edit':   can_edit,
        'can_delete': can_delete,
    }


def calculate_stats_from_qs(queryset):
    """
    Calcula estadísticas del inventario directamente desde un QuerySet.
    Retorna dict con: total, low_stock_count, inventory_value, top_category.
    """
    from django.db import models as m
    total      = queryset.count()
    criticos   = queryset.filter(stock_actual__lt=m.F('stock_minimo')).count()
    valor      = Decimal('0')
    categorias = []

    for p in queryset:
        valor += p.precio_venta * p.stock_actual
        categorias.append(p.categoria.nombre)

    cats = Counter(categorias)
    top_category = cats.most_common(1)[0][0] if cats else None

    return {
        'total':           total,
        'low_stock_count': criticos,
        'inventory_value': valor,
        'top_category':    top_category,
    }


def calculate_stats(productos_data):
    """
    Calcula estadisticas de inventario desde un payload con count/results.
    Mantiene compatibilidad con pruebas y consumidores que no usan QuerySet.
    """
    productos = productos_data.get('results', [])
    total = productos_data.get('count', len(productos))
    low_stock_count = 0
    inventory_value = Decimal('0')
    categorias = []

    for producto in productos:
        precio = Decimal(str(producto.get('precio_venta', '0')))
        stock_actual = int(producto.get('stock_actual', 0))
        stock_minimo = int(producto.get('stock_minimo', 0))

        if stock_actual < stock_minimo:
            low_stock_count += 1

        inventory_value += precio * stock_actual
        categoria = producto.get('categoria_nombre')
        if categoria:
            categorias.append(categoria)

    cats = Counter(categorias)
    top_category = cats.most_common(1)[0][0] if cats else None

    return {
        'total': total,
        'low_stock_count': low_stock_count,
        'inventory_value': inventory_value,
        'top_category': top_category,
    }
