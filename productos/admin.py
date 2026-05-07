from django.contrib import admin
from .models import Categoria, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo', 'created_at']
    list_filter = ['activo', 'created_at']
    search_fields = ['nombre']
    ordering = ['nombre']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'precio_venta', 'costo', 'stock_actual', 'stock_minimo', 'stock_critico', 'activo']
    list_filter = ['activo', 'categoria', 'created_at']
    search_fields = ['nombre', 'codigo_barra']
    ordering = ['nombre']
    readonly_fields = ['created_at', 'updated_at', 'ganancia_unitaria']
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo_barra', 'nombre', 'categoria', 'descripcion')
        }),
        ('Precios', {
            'fields': ('precio_venta', 'costo', 'ganancia_unitaria')
        }),
        ('Inventario', {
            'fields': ('stock_actual', 'stock_minimo', 'unidad')
        }),
        ('Estado', {
            'fields': ('activo', 'created_at', 'updated_at')
        }),
    )
