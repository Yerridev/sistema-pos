from django.contrib import admin
from .models import Categoria, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo', 'creado_en']
    list_filter = ['activo', 'creado_en']
    search_fields = ['nombre']
    ordering = ['nombre']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'precio_venta', 'costo', 'stock_actual', 'stock_minimo', 'stock_critico', 'activo']
    list_filter = ['activo', 'categoria', 'creado_en']
    search_fields = ['nombre', 'codigo_barra']
    ordering = ['nombre']
    readonly_fields = ['creado_en', 'actualizado_en', 'ganancia_unitaria']
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
            'fields': ('activo', 'creado_en', 'actualizado_en')
        }),
    )
