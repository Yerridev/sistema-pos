# Backlog Refinado (Issues pequeños)

> Estado: **listo para crear en GitHub Issues**.
> 
> Nota: cada ítem está diseñado para 1–2 días de trabajo y referencia un issue padre existente.

---

## 1) Auth: Configurar JWT y endpoints de autenticación
**Relacionado con #3**

**Descripción**
Implementar configuración de JWT con login y refresh token para la API.

**Checklist**
- [ ] Instalar/configurar `djangorestframework-simplejwt`
- [ ] Crear endpoint de login
- [ ] Crear endpoint de refresh
- [ ] Validar expiración y renovación de token
- [ ] Agregar prueba básica de autenticación

---

## 2) Auth: Roles y permisos por módulo
**Relacionado con #3**

**Descripción**
Definir roles (`admin`, `cajero`, `supervisor`) y restringir acceso a endpoints críticos.

**Checklist**
- [ ] Crear modelo/flags de rol de usuario
- [ ] Configurar permisos DRF por rol
- [ ] Restringir endpoints de administración a `admin`
- [ ] Validar acceso de `cajero` a ventas/caja
- [ ] Agregar pruebas de autorización

---

## 3) Inventario: Modelo Producto con validaciones de negocio
**Relacionado con #4**

**Descripción**
Crear/ajustar modelo Producto con constraints de stock y reglas de precio.

**Checklist**
- [ ] Definir campos del modelo Producto
- [ ] Agregar constraint `stock_actual >= 0`
- [ ] Definir regla explícita: bloquear ventas por debajo del costo y requerir aprobación de supervisor para ventas al costo
- [ ] Crear índice para `codigo_barra`
- [ ] Crear migración y validar en PostgreSQL

---

## 4) Inventario: API de búsqueda y listado de stock crítico
**Relacionado con #4**

**Descripción**
Implementar endpoints para búsqueda de productos y reporte de stock crítico.

**Checklist**
- [ ] Implementar `GET /api/productos/buscar/?q=`
- [ ] Implementar `GET /api/reportes/stock-critico/`
- [ ] Agregar filtros por nombre/código/categoría
- [ ] Agregar paginación en listado
- [ ] Agregar pruebas de búsqueda y stock crítico

---

## 5) Caja: Apertura de caja con reglas de estado
**Relacionado con #5**

**Descripción**
Implementar apertura de caja validando que no exista una caja abierta para el turno.

**Checklist**
- [ ] Implementar `POST /api/cajas/{id}/apertura/`
- [ ] Validar estado previo de caja
- [ ] Registrar saldo inicial y fecha de apertura
- [ ] Retornar errores de negocio consistentes
- [ ] Agregar pruebas de apertura

---

## 6) Caja: Cierre y cuadre automático
**Relacionado con #5**

**Descripción**
Implementar cierre de caja con cálculo de ingresos, egresos y diferencia final.

**Checklist**
- [ ] Implementar `POST /api/cajas/{id}/cierre/`
- [ ] Calcular `saldo_final` automáticamente
- [ ] Persistir diferencia de cuadre
- [ ] Bloquear cierre de caja ya cerrada
- [ ] Agregar pruebas de cuadre

---

## 7) Ventas: Registro atómico de venta y descuento de stock
**Relacionado con #6**

**Descripción**
Registrar venta en transacción atómica, descontando stock y actualizando caja.

**Checklist**
- [ ] Implementar `POST /api/ventas/`
- [ ] Validar caja abierta antes de vender
- [ ] Validar stock disponible por ítem
- [ ] Aplicar transacción atómica para venta + stock + caja
- [ ] Agregar pruebas del flujo completo de venta

---

## 8) Ventas: Anulación de venta con motivo obligatorio
**Relacionado con #6**

**Descripción**
Permitir anular ventas sin eliminar registros, guardando motivo y trazabilidad.

**Checklist**
- [ ] Implementar `POST /api/ventas/{id}/anular/`
- [ ] Exigir motivo obligatorio
- [ ] Cambiar estado a `ANULADA`
- [ ] Registrar usuario y timestamp de anulación
- [ ] Agregar pruebas de anulación

---

## 9) Compras: Registro de compras con actualización de stock
**Relacionado con #7**

**Descripción**
Registrar compra y actualizar stock por detalle de productos.

**Checklist**
- [ ] Implementar modelo `Compra` y `DetalleCompra`
- [ ] Implementar `POST /api/compras/`
- [ ] Incrementar stock al confirmar compra
- [ ] Validar consistencia de totales
- [ ] Agregar pruebas de actualización de stock por compra

---

## 10) Reportes: Ventas del día y top productos
**Relacionado con #7**

**Descripción**
Crear endpoint de reporte diario de ventas con métricas por método de pago y top productos.

**Checklist**
- [ ] Implementar `GET /api/reportes/ventas-del-dia/`
- [ ] Incluir total diario y desglose por método de pago
- [ ] Calcular top 5 productos vendidos
- [ ] Validar filtros por fecha/hora
- [ ] Agregar pruebas de reporte diario
