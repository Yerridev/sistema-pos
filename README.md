# Sistema de Punto de Venta (POS)

## Descripción
Sistema para gestionar ventas en mostrador, control de inventario, apertura y cierre de caja, y reportes de ventas diarios y por producto. Orientado a negocios retail, permite una gestión eficiente de productos, proveedores, compras y ventas.

El sistema cuenta con roles diferenciados:
- **Admin**: acceso completo a todas las funcionalidades y reportes.
- **Cajero**: acceso limitado a ventas y apertura/cierre de caja.

---

## Integrantes del Grupo 6
- Chilcon Ramirez Abondanyerri
- Chinchay Campos Jhon Jairo
- Puluche Espejo Pietro Ralf
- Bardales Vasquez Keysi Jeanpierre
- Hidrogo Mateo Jeslyn Nicole

---

## Tecnologías
- **Backend:** Django + Django REST Framework
- **Frontend:** Django Templates + Bootstrap 5 *(alternativa: React/Vue + API REST)*
- **Base de datos:** PostgreSQL / SQLite para desarrollo
- **Autenticación:** JWT con roles (Admin, Cajero)
- **Testing:** Pytest / Django Test Framework
- **Documentación API:** Swagger/OpenAPI

---

## Modelos Principales
- **Producto:** `codigo_barra, nombre, categoria, precio_venta, costo, stock_actual, stock_minimo, unidad`
- **Proveedor:** `nombre, ruc, contacto`
- **Venta:** `cajero, caja, fecha, subtotal, descuento, igv, total, metodo_pago, estado`
- **DetalleVenta:** `venta, producto, cantidad, precio_unitario, descuento_linea, subtotal`
- **Caja:** `nombre, saldo_inicial, saldo_final, fecha_apertura, fecha_cierre, cajero, estado`
- **MovimientoCaja:** `caja, tipo(INGRESO/EGRESO), monto, concepto`
- **Compra:** `proveedor, fecha, total, estado`
- **DetalleCompra:** `compra, producto, cantidad, costo_unitario`

---

## Funcionalidades Principales

### Ventas
- Registrar venta con actualización de stock y caja.
- Validación de stock y caja abierta.
- Generación de ticket de venta.

### Caja
- Apertura y cierre de caja con cálculo automático de diferencias.
- Registro de movimientos de ingreso/egreso.
- Cuadre automático de caja.

### Inventario
- CRUD completo de productos.
- Alertas de stock crítico.
- Búsqueda y filtrado por nombre/código de barras y categoría.

### Compras
- Registro de entrada de mercadería.
- Actualización automática de stock.

### Reportes
- Ventas del día: totales por método de pago, top productos.
- Stock crítico: productos bajo mínimo con sugerencias de reposición.
- Utilidad: ingresos vs costos por período.

### Autenticación y Roles
- JWT con roles diferenciados (Admin, Cajero).
- Cajero restringido a ventas y caja.
- Admin con acceso completo a reportes y compras.

---

## Flujo de Trabajo

1. **Crear rama desde `develop`**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/nombre-tarea
   ```

2. **Hacer commits con Convencional Commits**
   ```bash
   git add .
   git commit -m "feat: implementar validación de stock en ventas"
   ```

3. **Abrir Pull Request hacia `develop`**
   - El PR debe referenciar su issue (`Closes #numero`).
   - El PR debe incluir pasos de prueba y checklist completo.
   - No se permite push directo a `main` o `develop`.

4. **Merge del Pull Request**
   - Requiere al menos 1 aprobación del reviewer/líder.
   - Debe estar actualizado con `develop` y sin conflictos.
   - Solo cambios validados en `develop` pueden promocionarse a `main`.

---

## Organización del Equipo

### Roles
- **Líder / Reviewer**
  - Prioriza backlog junto al equipo.
  - Revisa PRs, valida estándares y autoriza merges.
  - Monitorea riesgos de integración y calidad.

- **Responsables por módulo**
  - **Auth y Seguridad:** autenticación, permisos y roles.
  - **Ventas y Caja:** flujo de cobro, transacciones y cuadre.
  - **Inventario y Compras:** stock, reposición y proveedores.
  - **Reportes y Dashboard:** métricas, reportes operativos y vista admin.

### Responsabilidades básicas
- Cada desarrollador mantiene su módulo estable y documentado.
- Todo cambio se trabaja en `feature/*` y se integra por PR.
- El responsable de módulo da contexto funcional durante la revisión.
- El reviewer valida impacto transversal antes del merge.

---

## Riesgos y Prevención

1. **Conflictos de merge**
   - **Riesgo:** cambios simultáneos sobre los mismos archivos.
   - **Prevención:** ramas pequeñas, PRs frecuentes y sincronización diaria con `develop`.

2. **Problemas con migraciones**
   - **Riesgo:** migraciones en conflicto o fuera de orden.
   - **Prevención:** generar migraciones por tarea, revisar dependencias y probar `migrate` antes del PR.

3. **Errores de integración entre módulos**
   - **Riesgo:** romper flujos por cambios acoplados entre apps.
   - **Prevención:** contratos de API claros, pruebas de integración y validación cruzada en `develop`.

---

## Instalación Rápida (Desarrollo)
```bash
# Clonar repositorio
git clone https://github.com/Yerridev/sistema-pos.git
cd sistema-pos

# Crear entorno virtual
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

# Instalar dependencias
pip install -r requirements.txt

# Migrar base de datos
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Ejecutar servidor
python manage.py runserver
```
