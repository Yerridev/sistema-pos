# Plan de Tareas — Bardales Vasquez Keysi Jeanpierre

**Módulo:** Frontend — Gráficos Reportes + Dashboard Admin
**Rubrica:** Frontend Web (15%)

---

## Contexto Actual

La página de reportes (`templates/dashboard/reportes.html`) solo tiene tablas y stat cards, sin gráficos. No existe un Dashboard Admin unificado que muestre ventas del día, caja actual y alertas de stock crítico en una sola vista. No hay librería de gráficos cargada.

Archivos clave:
- `templates/dashboard/reportes.html` — 135 líneas, solo tablas y CSS bars
- `templates/base.html` — Master layout con Tailwind CSS (CDN)
- `templates/components/sidebar.html` — Sidebar con navegación
- `ventas/dashboard_views.py` — Views para dashboards de ventas y caja
- `productos/views.py:139` — `InventarioDashboardView`
- `reportes/views.py` — `reportes_dashboard()` view
- No hay Chart.js, ApexCharts, ni ninguna librería de charts en el proyecto

---

## Tarea 1: Agregar librería de gráficos

### 1.1 Agregar Chart.js a `base.html`

En `templates/base.html`, agregar antes de `</body>`:

```html
<!-- Chart.js CDN -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
```

**Alternativa:** Si preferís ApexCharts (más moderno, mejor para dashboards):
```html
<script src="https://cdn.jsdelivr.net/npm/apexcharts@3.54.1/dist/apexcharts.min.js"></script>
```

Recomendación: **Chart.js** es más simple, más ligero, y suficiente para estos reportes.

---

## Tarea 2: Agregar gráficos a la página de Reportes

### 2.1 Gráfico de Torta — Ventas por Método de Pago

En `templates/dashboard/reportes.html`, agregar un `<canvas>` dentro de la sección "Ventas del día":

```html
<!-- Después de la sección de totales por método -->
<div class="mt-lg">
  <h3 class="text-sm font-semibold text-text-primary dark:text-[#E8E9EC]">Ventas por método de pago</h3>
  <div class="mt-sm" style="max-width: 300px;">
    <canvas id="chartMetodoPago"></canvas>
  </div>
</div>
```

Al final del archivo, agregar script:

```html
{% block extra_js %}
<script>
document.addEventListener('DOMContentLoaded', function() {
  const ctx = document.getElementById('chartMetodoPago');
  if (ctx) {
    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: [{% for metodo, total in ventas_dia.por_metodo.items %}'{{ metodo }}'{% if not forloop.last %},{% endif %}{% endfor %}],
        datasets: [{
          data: [{% for metodo, total in ventas_dia.por_metodo.items %}{{ total }}{% if not forloop.last %},{% endif %}{% endfor %}],
          backgroundColor: ['#22c55e', '#3b82f6', '#f59e0b'],
          borderWidth: 0,
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom' }
        }
      }
    });
  }
});
</script>
{% endblock %}
```

### 2.2 Gráfico de Barras — Top 5 Productos

Agregar un `<canvas>` en la sección "Top 5 productos":

```html
<div class="mt-lg">
  <h3 class="text-sm font-semibold text-text-primary dark:text-[#E8E9EC]">Top 5 productos</h3>
  <div class="mt-sm" style="height: 250px;">
    <canvas id="chartTopProductos"></canvas>
  </div>
</div>
```

Script:

```javascript
const ctxTop = document.getElementById('chartTopProductos');
if (ctxTop) {
  new Chart(ctxTop, {
    type: 'bar',
    data: {
      labels: [{% for item in ventas_dia.top_productos %}'{{ item.nombre|truncatechars:20 }}'{% if not forloop.last %},{% endif %}{% endfor %}],
      datasets: [{
        label: 'Unidades vendidas',
        data: [{% for item in ventas_dia.top_productos %}{{ item.cantidad }}{% if not forloop.last %},{% endif %}{% endfor %}],
        backgroundColor: '#6366f1',
        borderRadius: 4,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true } }
    }
  });
}
```

### 2.3 Gráfico de Líneas — Utilidad por Día

En la sección "Utilidad", agregar un `<canvas>` antes de la tabla:

```html
<div class="mt-lg" style="height: 200px;">
  <canvas id="chartUtilidad"></canvas>
</div>
```

Script:

```javascript
const ctxUtil = document.getElementById('chartUtilidad');
if (ctxUtil) {
  new Chart(ctxUtil, {
    type: 'line',
    data: {
      labels: [{% for dia in utilidad.por_dia %}'{{ dia.dia|date:"d/m" }}'{% if not forloop.last %},{% endif %}{% endfor %}],
      datasets: [{
        label: 'Utilidad (S/.)',
        data: [{% for dia in utilidad.por_dia %}{{ dia.total }}{% if not forloop.last %},{% endif %}{% endfor %}],
        borderColor: '#22c55e',
        backgroundColor: 'rgba(34,197,94,0.1)',
        fill: true,
        tension: 0.3,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } }
    }
  });
}
```

---

## Tarea 3: Crear Dashboard Admin Unificado

### 3.1 Crear `reportes/views.py` — Vista del Dashboard Admin

Agregar una nueva view que combine datos de ventas del día, caja actual y stock crítico:

```python
@login_required
@user_passes_test(_is_admin)
def admin_dashboard(request):
    """Dashboard principal del admin con métricas clave."""
    from caja.models import Caja
    from django.db.models import Sum

    fecha = timezone.localdate()

    # Ventas del día
    ventas_data = ReporteService.ventas_del_dia(fecha)

    # Cajas abiertas
    cajas_abiertas = Caja.objects.filter(estado="ABIERTA").select_related("cajero")
    cajas_info = []
    for caja in cajas_abiertas:
        cajas_info.append({
            "id": caja.id,
            "nombre": caja.nombre,
            "cajero": caja.cajero.get_full_name() or caja.cajero.username,
            "saldo_actual": caja.saldo_actual,
            "fecha_apertura": caja.fecha_apertura,
        })

    # Stock crítico
    stock_critico = ReporteService.stock_critico()

    return render(request, "dashboard/admin_dashboard.html", {
        "ventas_dia": ventas_data,
        "cajas_abiertas": cajas_info,
        "stock_critico": stock_critico,
        "page_title": "Dashboard Admin",
        "active_nav": "admin:dashboard",
    })
```

### 3.2 Crear template `templates/dashboard/admin_dashboard.html`

```html
{% extends "base.html" %}

{% block title %}Dashboard Admin - Cobrate POS{% endblock %}

{% block content %}
<div class="flex flex-col gap-xl">
  <!-- Stats Cards -->
  <section class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-md">
    <article class="bg-white dark:bg-[#1E2128] rounded-xl shadow-sm border border-border-subtle dark:border-white/10 p-lg">
      <p class="text-caption-xs text-text-secondary dark:text-slate-400">Ventas hoy</p>
      <p class="mt-xs text-3xl font-bold text-text-primary dark:text-[#E8E9EC]">{{ ventas_dia.cantidad }}</p>
      <p class="text-sm text-text-secondary dark:text-slate-400">S/. {{ ventas_dia.total }}</p>
    </article>
    <article class="bg-white dark:bg-[#1E2128] rounded-xl shadow-sm border border-border-subtle dark:border-white/10 p-lg">
      <p class="text-caption-xs text-text-secondary dark:text-slate-400">Cajas abiertas</p>
      <p class="mt-xs text-3xl font-bold text-primary">{{ cajas_abiertas|length }}</p>
    </article>
    <article class="bg-white dark:bg-[#1E2128] rounded-xl shadow-sm border border-border-subtle dark:border-white/10 p-lg">
      <p class="text-caption-xs text-text-secondary dark:text-slate-400">Stock crítico</p>
      <p class="mt-xs text-3xl font-bold text-error">{{ stock_critico|length }}</p>
    </article>
    <article class="bg-white dark:bg-[#1E2128] rounded-xl shadow-sm border border-border-subtle dark:border-white/10 p-lg">
      <p class="text-caption-xs text-text-secondary dark:text-slate-400">Total ventas S/.</p>
      <p class="mt-xs text-3xl font-bold text-primary">{{ ventas_dia.total }}</p>
    </article>
  </section>

  <!-- Gráfico de ventas por método -->
  <section class="grid grid-cols-1 xl:grid-cols-2 gap-md">
    <article class="bg-white dark:bg-[#1E2128] rounded-xl shadow-sm border border-border-subtle dark:border-white/10 p-lg">
      <h2 class="font-semibold text-text-primary dark:text-[#E8E9EC]">Ventas por método</h2>
      <div class="mt-md" style="max-width: 350px;">
        <canvas id="chartMetodo"></canvas>
      </div>
    </article>
    <article class="bg-white dark:bg-[#1E2128] rounded-xl shadow-sm border border-border-subtle dark:border-white/10 p-lg">
      <h2 class="font-semibold text-text-primary dark:text-[#E8E9EC]">Top productos hoy</h2>
      <div class="mt-md" style="height: 250px;">
        <canvas id="chartTop"></canvas>
      </div>
    </article>
  </section>

  <!-- Cajas abiertas -->
  <section class="bg-white dark:bg-[#1E2128] rounded-xl shadow-sm border border-border-subtle dark:border-white/10 overflow-hidden">
    <div class="px-lg py-md border-b border-border-subtle dark:border-white/10">
      <h2 class="font-semibold text-text-primary dark:text-[#E8E9EC]">Cajas abiertas</h2>
    </div>
    <div class="overflow-x-auto">
      <table class="w-full text-left text-sm">
        <thead class="bg-slate-50 dark:bg-white/5">
          <tr>
            <th class="px-lg py-sm text-caption-xs text-text-secondary dark:text-slate-400 uppercase">Caja</th>
            <th class="px-lg py-sm text-caption-xs text-text-secondary dark:text-slate-400 uppercase">Cajero</th>
            <th class="px-lg py-sm text-caption-xs text-text-secondary dark:text-slate-400 uppercase text-right">Saldo actual</th>
            <th class="px-lg py-sm text-caption-xs text-text-secondary dark:text-slate-400 uppercase">Abierta desde</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border-subtle dark:divide-white/10">
          {% for caja in cajas_abiertas %}
          <tr>
            <td class="px-lg py-sm font-medium">{{ caja.nombre }}</td>
            <td class="px-lg py-sm">{{ caja.cajero }}</td>
            <td class="px-lg py-sm text-right font-mono">S/. {{ caja.saldo_actual }}</td>
            <td class="px-lg py-sm">{{ caja.fecha_apertura|date:"d/m/Y H:i" }}</td>
          </tr>
          {% empty %}
          <tr><td colspan="4" class="px-lg py-xxl text-center text-text-secondary dark:text-slate-400">No hay cajas abiertas.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </section>

  <!-- Stock crítico resumen -->
  <section class="bg-white dark:bg-[#1E2128] rounded-xl shadow-sm border border-border-subtle dark:border-white/10 overflow-hidden">
    <div class="px-lg py-md border-b border-border-subtle dark:border-white/10">
      <h2 class="font-semibold text-text-primary dark:text-[#E8E9EC]">Alertas de stock crítico</h2>
    </div>
    <div class="overflow-x-auto">
      <table class="w-full text-left text-sm">
        <thead class="bg-slate-50 dark:bg-white/5">
          <tr>
            <th class="px-lg py-sm">Producto</th>
            <th class="px-lg py-sm">Stock</th>
            <th class="px-lg py-sm">Mínimo</th>
            <th class="px-lg py-sm text-right">Sugerencia</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border-subtle dark:divide-white/10">
          {% for prod in stock_critico %}
          <tr class="bg-red-50">
            <td class="px-lg py-sm font-medium">{{ prod.nombre }}</td>
            <td class="px-lg py-sm text-error font-mono">{{ prod.stock_actual }}</td>
            <td class="px-lg py-sm font-mono">{{ prod.stock_minimo }}</td>
            <td class="px-lg py-sm text-right font-mono">{{ prod.sugerencia_reposicion }}</td>
          </tr>
          {% empty %}
          <tr><td colspan="4" class="px-lg py-xxl text-center text-text-secondary">Sin alertas.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </section>
</div>

{% block extra_js %}
<script>
document.addEventListener('DOMContentLoaded', function() {
  // Gráfico de torta: Métodos de pago
  const ctx1 = document.getElementById('chartMetodo');
  if (ctx1) {
    new Chart(ctx1, {
      type: 'doughnut',
      data: {
        labels: [{% for metodo, total in ventas_dia.por_metodo.items %}'{{ metodo }}'{% if not forloop.last %},{% endif %}{% endfor %}],
        datasets: [{
          data: [{% for metodo, total in ventas_dia.por_metodo.items %}{{ total }}{% if not forloop.last %},{% endif %}{% endfor %}],
          backgroundColor: ['#22c55e', '#3b82f6', '#f59e0b'],
          borderWidth: 0,
        }]
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
  }

  // Gráfico de barras: Top productos
  const ctx2 = document.getElementById('chartTop');
  if (ctx2) {
    new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: [{% for item in ventas_dia.top_productos %}'{{ item.nombre|truncatechars:20 }}'{% if not forloop.last %},{% endif %}{% endfor %}],
        datasets: [{
          label: 'Unidades',
          data: [{% for item in ventas_dia.top_productos %}{{ item.cantidad }}{% if not forloop.last %},{% endif %}{% endfor %}],
          backgroundColor: '#6366f1',
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true } }
      }
    });
  }
});
</script>
{% endblock %}
{% endblock %}
```

### 3.3 Registrar URL del Dashboard Admin

En `reportes/urls.py` (o crear si no existe):

```python
from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('dashboard/reportes/', views.reportes_dashboard, name='dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
]
```

### 3.4 Agregar enlace al sidebar

En `templates/components/sidebar.html`, agregar dentro del bloque admin:

```html
{% if user.rol == 'admin' %}
<a href="{% url 'reportes:admin_dashboard' %}" class="...">
  <svg>...</svg>
  <span>Dashboard</span>
</a>
{% endif %}
```

---

## Checklist de Validación

- [ ] Chart.js cargado en `base.html`
- [ ] Gráfico de torta en reportes de ventas por método de pago
- [ ] Gráfico de barras horizontal en top 5 productos
- [ ] Gráfico de líneas en utilidad por día
- [ ] Dashboard Admin unificado creado (`admin_dashboard.html`)
- [ ] Dashboard Admin muestra: ventas del día, cajas abiertas, stock crítico
- [ ] Gráficos en Dashboard Admin
- [ ] URL registrada y sidebar actualizado
- [ ] Gráficos se adaptan a dark mode
- [ ] Responsive funciona en mobile

---

## Commits Convencionales Sugeridos

```
feat(templates): agregar Chart.js CDN a base.html
feat(reportes): agregar gráficos de torta, barras y líneas a reportes.html
feat(reportes): crear Dashboard Admin unificado con métricas y gráficos
feat(reportes): registrar URL y enlace en sidebar para Dashboard Admin
```

---

## ⚠️ CONTEXTO IMPORTANTE: Cambios de ModeloBase (commit acb3241 en develop)

> **Antes de empezar, pulled `develop` y lee esto.** Estos cambios ya están implementados y afectan directamente tu trabajo.

### Qué cambió en tus archivos clave

| Archivo | Cambio | Impacto en tu trabajo |
|---------|--------|----------------------|
| `templates/dashboard/reportes.html` | Sin cambios | Tus gráficos se agregan AQUÍ — solo tablas y stat cards existentes |
| `templates/base.html` | Sin cambios | Chart.js CDN se agrega AQUÍ antes de `</body>` |
| `templates/components/sidebar.html` | Sin cambios | Enlace al dashboard admin se agrega AQUÍ |
| `reportes/views.py` | Sin cambios de ModeloBase | La view `admin_dashboard` se crea AQUÍ |
| `ventas/dashboard_views.py` | `buscar_productos_venta()` usa `Producto.objects.filter(activo=True)` | Tus queries de ventas del día también deberían filtrar por `activo=True` |

### Cómo obtener los datos para tus gráficos

Los datos vienen de las views que ya existen. Para tu Dashboard Admin, necesitás combinar:

```python
# En reportes/views.py — tu nueva view admin_dashboard
from django.db.models import Sum
from caja.models import Caja
from ventas.models import Venta, DetalleVenta
from productos.models import Producto

def admin_dashboard(request):
    fecha = timezone.localdate()
    
    # Ventas del día
    ventas = Venta.objects.filter(fecha__date=fecha, estado="COMPLETADA")
    total_ventas = ventas.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    cantidad_ventas = ventas.count()
    
    # Por método de pago
    por_metodo = {
        item["metodo_pago"]: item["total"] or Decimal("0.00")
        for item in ventas.values("metodo_pago").annotate(total=Sum("total"))
    }
    
    # Top productos
    top_productos = list(
        DetalleVenta.objects.filter(venta__in=ventas)
        .values(nombre=F("producto__nombre"))
        .annotate(cantidad=Sum("cantidad"))
        .order_by("-cantidad")[:5]
    )
    
    # Cajas abiertas
    cajas_abiertas = Caja.objects.filter(estado="ABIERTA").select_related("cajero")
    
    # Stock crítico
    stock_critico = Producto.objects.filter(
        activo=True, stock_actual__lt=F("stock_minimo")
    ).select_related("categoria")
```

### Template tags de Django para los gráficos

En tus templates, usá estos tags para pasar datos a JavaScript:

```html
<!-- Para listas de diccionarios (por_metodo) -->
labels: [{% for metodo, total in ventas_dia.por_metodo.items %}'{{ metodo }}'{% if not forloop.last %},{% endif %}{% endfor %}],
data: [{% for metodo, total in ventas_dia.por_metodo.items %}{{ total }}{% if not forloop.last %},{% endif %}{% endfor %}],

<!-- Para queryset de top productos -->
labels: [{% for item in ventas_dia.top_productos %}'{{ item.nombre|truncatechars:20 }}'{% if not forloop.last %},{% endif %}{% endfor %}],
```

### CSS classes del proyecto (Tailwind)

El proyecto usa un design system custom. Estas son las clases que ya existen en los templates:

- **Cards:** `bg-white dark:bg-[#1E2128] rounded-xl shadow-sm border border-border-subtle dark:border-white/10 p-lg`
- **Text primary:** `text-text-primary dark:text-[#E8E9EC]`
- **Text secondary:** `text-text-secondary dark:text-slate-400`
- **Text error:** `text-error`
- **Primary color:** `text-primary`
- **Spacing:** `gap-md`, `gap-lg`, `gap-xl`, `p-sm`, `p-md`, `p-lg`
- **Grid:** `grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-md`

### Orden de trabajo

1. **Esperá a que Puluche termine `reportes/services.py`** para usar `ReporteService` en tu dashboard
2. Mientras tanto, podés crear los gráficos en `reportes.html` que no depende de nadie
3. Después creá el dashboard admin y la URL
