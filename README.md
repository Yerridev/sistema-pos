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

## Flujo de Trabajo Colaborativo
1. **Ramas principales**
   - `main`: versión estable
   - `develop`: integración de funcionalidades

2. **Ramas de desarrollo**
   - Cada integrante crea su branch:
     ```
     git checkout -b feature/nombre-funcionalidad
     ```
   - Commit claros y atómicos:
     ```
     feat: agregar búsqueda de productos
     fix: corregir cálculo de total en ventas
     docs: actualizar README con endpoints
     ```

3. **Pull Requests**
   - Abrir PR hacia `develop`
   - Revisar y aprobar antes de merge
   - Merge a `main` solo cuando esté estable

4. **Roles en GitHub**
   - Todos los integrantes tienen permisos de **Write**
   - `main` protegida con branch protection rules

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
