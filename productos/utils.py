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
