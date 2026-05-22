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
- **Backend:** Django 5.2 + Django REST Framework 3.17
- **Frontend:** Django Templates + Tailwind CSS *(alternativa: Next.js + API REST)*
- **Base de datos:** PostgreSQL 15
- **Autenticación:** SimpleJWT con roles (Admin, Cajero)
- **Documentación API:** Swagger/OpenAPI (drf-spectacular)
- **Containerización:** Docker Compose
- **Testing:** Django Test Framework

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

### Autenticación ✅
- Login con username + password vía `/api/token/`
- Renovación de tokens vía `/api/token/refresh/`
- Roles en response: `admin`, `cajero`, `supervisor`
- Página de login en `/login/`

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

### Roles y Permisos
- JWT con roles diferenciados (Admin, Cajero, Supervisor).
- Cajero restringido a ventas y caja.
- Admin con acceso completo a reportes y compras.

---

---

## Instalación con Docker Compose (Recomendado)

### Requisitos
- Docker Desktop instalado
- Git

### 1. Clonar repositorio
```bash
git clone https://github.com/Yerridev/sistema-pos.git
cd sistema-pos
```

### 2. Configurar variables de entorno
```bash
# Copiar ejemplo y editar con tus valores
copy .env.example .env

# Editar .env con tus datos:
# SECRET_KEY=tu-clave-secreta-generada
# DEBUG=True
# DB_NAME=pos_db
# DB_USER=postgres
# DB_PASSWORD=tu_password_seguro
# DB_HOST=db
# DB_PORT=5432
```

### 3. Generar SECRET_KEY
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. Levantar servicios
```bash
docker compose up -d
```

### 5. Crear superusuario
```bash
docker compose exec web python manage.py createsuperuser
```

### 6. Verificar que funcione
- **API:** http://localhost:8000/api/docs/ (Swagger)
- **Login:** http://localhost:8000/login/
- **Admin:** http://localhost:8000/admin/

### Comandos Docker útiles
```bash
# Ver logs
docker compose logs -f web

# Detener servicios
docker compose down

# Reiniciar servicios
docker compose restart

# Solo base de datos
docker compose up -d db
```

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

## Instalación Local (Sin Docker)

### Requisitos
- Python 3.11+
- PostgreSQL 15 corriendo en puerto 5432

### 1. Clonar repositorio
```bash
git clone https://github.com/Yerridev/sistema-pos.git
cd sistema-pos
```

### 2. Crear entorno virtual
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux/Mac
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
copy .env.example .env

# Editar .env:
# DB_HOST=localhost (NO usar 'db' en desarrollo local)
```

### 5. Crear base de datos PostgreSQL
```sql
CREATE DATABASE pos_db;
CREATE USER postgres WITH PASSWORD 'tu_password';
GRANT ALL PRIVILEGES ON DATABASE pos_db TO postgres;
```

### 6. Migrar base de datos
```bash
python manage.py migrate
```

### 7. Crear superusuario
```bash
python manage.py createsuperuser
```

### 8. Ejecutar servidor
```bash
python manage.py runserver
```

---

## Endpoints de API

### Autenticación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/token/` | Login — retorna access + refresh tokens + rol |
| POST | `/api/token/refresh/` | Renovar access token |
| GET | `/login/` | Página de login (frontend) |

### Documentación
| Endpoint | Descripción |
|----------|-------------|
| `/api/docs/` | Swagger UI |
| `/api/schema/` | OpenAPI Schema (JSON) |

### Uso de tokens
```bash
# Login
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'

# Usar token en requests
curl -X GET http://localhost:8000/api/productos/ \
  -H "Authorization: Bearer <tu_access_token>"
```

---

## Flujo de Trabajo Colaborativo

### Ramas
- `main`: versión estable
- `develop`: integración de funcionalidades
- `feature/nombre-funcionalidad`: desarrollo individual

### Commits convencionales
```
feat: agregar nueva funcionalidad
fix: corregir bug
docs: actualizar documentación
test: agregar tests
refactor: refactorizar código
```

---

## Implementacion actual: Caja y Categorias

### Caja

Ruta principal: http://localhost:8000/dashboard/caja/

Permisos:
- **Admin:** puede ver y gestionar cajas de todos los usuarios.
- **Cajero:** solo ve y gestiona sus propias cajas.

Flujo disponible:
1. Abrir caja con nombre y saldo inicial.
2. Registrar movimientos de caja: `INGRESO` y `EGRESO`.
3. Ver saldo actual calculado como `saldo_inicial + ingresos - egresos`.
4. Cerrar caja. El sistema guarda `saldo_final`, `fecha_cierre` y cambia el estado a `CERRADA`.

Rutas web internas:
- `POST /dashboard/caja/abrir/`
- `POST /dashboard/caja/<id>/movimiento/`
- `POST /dashboard/caja/<id>/cerrar/`

API REST:
- `GET/POST /api/cajas/`
- `POST /api/cajas/<id>/abrir/`
- `POST /api/cajas/<id>/cerrar/`

### Categorias

Ruta principal: http://localhost:8000/dashboard/inventario/

En el dashboard de inventario, el rol **admin** tiene el boton **Categorias** para:
- Crear categorias.
- Editar nombre y descripcion.
- Desactivar categorias que no tengan productos activos.

Las categorias activas se usan en:
- Filtro de inventario.
- Selector del modal de producto.
- API de productos y categorias.

Rutas web internas:
- `GET /dashboard/categorias/`
- `POST /dashboard/categorias/crear/`
- `GET/POST /dashboard/categorias/<id>/editar/`
- `POST /dashboard/categorias/<id>/eliminar/`

API REST:
- `GET/POST /api/categorias/`
- `GET/PUT/PATCH/DELETE /api/categorias/<id>/`

### Reportes

Ruta principal: http://localhost:8000/dashboard/reportes/

Permisos:
- **Admin:** accede a todos los reportes, incluyendo utilidad.
- **Cajero:** no accede al dashboard de reportes ni al reporte de utilidad.

Reportes disponibles:
- Ventas del dia con total general, totales por metodo de pago y top 5 productos.
- Stock critico con sugerencia de reposicion.
- Utilidad por periodo: ingresos vs costos.

API REST:
- `GET /api/reportes/ventas-del-dia/?fecha=YYYY-MM-DD`
- `GET /api/reportes/stock-critico/`
- `GET /api/reportes/utilidad/?desde=YYYY-MM-DD&hasta=YYYY-MM-DD`

### Compras y proveedores

API REST admin:
- `GET/POST /api/proveedores/`
- `GET/POST /api/compras/`

`POST /api/compras/` registra entrada de mercaderia, crea detalles de compra, actualiza el costo del producto e incrementa `stock_actual`.

Payload ejemplo:
```json
{
  "proveedor": 1,
  "detalles": [
    {"producto": 1, "cantidad": 10, "costo_unitario": "3.50"}
  ]
}
```

### Checklist frente a la rubrica

Cumplido:
- Modelos principales de producto, venta, detalle de venta, caja y movimiento de caja.
- Modelos de proveedor, compra y detalle de compra.
- Registro de venta atomico: valida caja abierta, descuenta stock y registra ingreso en caja.
- Apertura, cierre, movimientos y saldo actual de caja.
- Inventario con CRUD, filtros y alertas de stock critico.
- Reportes de ventas del dia, stock critico y utilidad.
- Swagger en `/api/docs/`.
- Roles `admin` y `cajero`, con compras/reportes restringidos a admin.

Pendiente o mejorable:
- Pantalla web completa de compras/entrada de mercaderia.
- Ticket imprimible/formato comprobante despues de cobrar.
- Tests de integracion suficientes para cubrir venta, caja, compras y reportes.
- Rol `supervisor` si el docente lo exige; actualmente existen `admin` y `cajero`.

### Pull Requests
- Crear PR hacia `develop`
- Revisar y aprobar antes de merge
- Merge a `main` solo cuando esté estable
