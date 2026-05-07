import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import models
from productos.models import Producto, Categoria

cat, _ = Categoria.objects.get_or_create(nombre='Abarrotes')
cat2, _ = Categoria.objects.get_or_create(nombre='Bebidas')

productos = [
    ('SKU-TEST-001', 'Arroz Integral 1kg', cat, 8.50, 6.00, 25, 10),
    ('SKU-TEST-002', 'Fideo Spaghetti 500g', cat, 4.20, 3.00, 50, 15),
    ('SKU-TEST-003', 'Aceite Vegetal 1L', cat, 12.00, 9.50, 3, 10),
    ('SKU-TEST-004', 'Azucar Rubia 1kg', cat, 5.50, 4.00, 100, 20),
    ('SKU-TEST-005', 'Sal Marina 500g', cat, 3.00, 2.00, 5, 10),
    ('SKU-TEST-006', 'Cerveza Cusqueña 650ml', cat2, 7.00, 5.00, 48, 12),
    ('SKU-TEST-007', 'Gaseosa Inca Kola 2L', cat2, 6.50, 4.50, 30, 10),
]

for codigo, nombre, categoria, precio_venta, costo, stock_actual, stock_minimo in productos:
    Producto.objects.get_or_create(
        codigo_barra=codigo,
        defaults={
            'nombre': nombre,
            'categoria': categoria,
            'precio_venta': precio_venta,
            'costo': costo,
            'stock_actual': stock_actual,
            'stock_minimo': stock_minimo,
            'activo': True,
        }
    )

print(f'Productos creados: {Producto.objects.count()}')

criticos = Producto.objects.filter(stock_actual__lt=models.F('stock_minimo'))
print(f'Productos con stock critico: {criticos.count()}')
for p in criticos:
    print(f'  - {p.nombre}: stock={p.stock_actual}, min={p.stock_minimo}')