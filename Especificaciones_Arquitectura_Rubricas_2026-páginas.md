## **TALLER DE LENGUAJES DE PROGRAMACIÓN** 

## **Especificaciones, Arquitectura y Rúbricas** 

_Proyectos Integradores — Solución Web Completa — Ciclo 2026-01_ 

## **9 Proyectos disponibles** 

- 

- 

- 

- 

- 

- 

- 

- 

- 

1. Plataforma de Delivery Local 

2. Sistema de Punto de Venta (POS) 

3. Venta de Pasajes Terrestres Interprovinciales 

4. Optimización de Rutas de Distribución 

5. Facturación Electrónica SUNAT-ready 

6. Picking Inteligente para Almacenes 

7. Sistema de Gestión Hotelera 

8. Gestión para Restaurantes y Food Service 

9. Control Nutricional y Tracking de Hábitos 

**Naturaleza del entregable: Solución web completa (backend Django/DRF + frontend web) con requerimientos arquitectónicos escalonados.** 

|**Componente**|**Peso**|**Descripción**|
|---|---|---|
|Modelos y Base de Datos|**10%**|Diseño correcto de entidades, relaciones e índices|
|API REST|**10%**|Endpoints completos, códigos HTTP, validaciones,<br>paginación|
|Lógica de Negocio Específica|**10%**|Reglas y flujos críticos del dominio implementados|
|Frontend Web|**15%**|Vistas funcionales, conectadas a la API, UX usable|
|Integración API–Frontend + Auth|**10%**|Token en headers, errores en UI, vistas protegidas por rol|
|Nivel 1 — Service Layer +<br>Excepciones|**15%**|Capa de servicios completa, excepciones de dominio propias|
|Nivel 1 — Soft Delete + Docker|**10%**|Modelo base abstracto, soft delete, Docker Compose<br>funcional|
|Nivel 2 — Patrón Arquitectónico<br>elegido|**15%**|Uno de: Repository, Strategy, Celery, Redis, Events,<br>WebSockets|
|Testing|**5%**|Tests unitarios e integración, cobertura ≥ 60%|
|Documentación y Calidad de<br>Código|**5%**|README, Swagger, instrucciones de despliegue, clean code,<br>sin N+1|



⭐ **BONUS — Nivel 3: Arquitectura Hexagonal (+10 puntos sobre la nota final)** 

• El directorio dominio/ no puede importar nada de Django. Entidades de dominio como dataclasses Python puras. 

• Puertos definidos como Protocols (interfaces). Adaptadores en infraestructura/ implementan los puertos. 

• Views de Django solo reciben el request y llaman al dominio. Tests de dominio sin base de datos (mocks). 

## **REQUERIMIENTOS ARQUITECTÓNICOS** 

## _Aplican a los 9 proyectos_ 

## **NIVEL 1 — Obligatorio para todos los proyectos (25% de la nota)** 

- Service Layer: una clase XxxService por módulo con toda la lógica de negocio. Las Views solo reciben el request, llaman al servicio y devuelven el response. 

• Excepciones de Dominio: jerarquía propia en exceptions.py. Clases específicas como AsientoNoDisponible, CajaNoAbierta, CapacidadExcedida. Nunca lanzar ValueError o Exception genéricos. 

- Soft Delete + Auditoría: modelo base abstracto con creado_en, actualizado_en, creado_por (FK a User), activo. Método eliminar() que hace soft delete. Todo modelo del sistema hereda de él. 

- Docker Compose: el proyecto debe levantarse con "docker compose up --build". Incluye Django + PostgreSQL + Redis (si aplica). Archivo .env.example con todas las variables requeridas. 

## **Ejemplo — Service Layer** 

`#` ❌ `MAL — Lógica en la View` 

```
class PedidoViewSet(viewsets.ModelViewSet):
```

```
    def create(self, request):
        producto = Producto.objects.get(pk=request.data["producto_id"])
```

```
        if producto.stock == 0:
```

```
            return Response({"error": "Sin stock"}, status=400)
```

```
        pedido = Pedido.objects.create(...)
```

```
        producto.stock -= 1
        producto.save()
```

```
        return Response(PedidoSerializer(pedido).data, status=201)
```

`#` ✅ `BIEN — View delgada, Service con la lógica` 

```
class PedidoViewSet(viewsets.ModelViewSet):
    def create(self, request):
        try:
            pedido = PedidoService.crear(request.data, usuario=request.user)
            return Response(PedidoSerializer(pedido).data, status=201)
        except ProductoSinStock as e:
            return Response({"error": str(e)}, status=400)
```

```
        except NegocioCerrado as e:
```

```
# services.py
class PedidoService:
    @staticmethod
    @transaction.atomic
    def crear(data: dict, usuario) -> Pedido:
        producto = Producto.objects.select_for_update().get(pk=data["producto_id"])
```

```
        if producto.stock == 0:
            raise ProductoSinStock(f"{producto.nombre} no tiene stock disponible")
        if not NegocioService.esta_abierto(data["negocio_id"]):
            raise NegocioCerrado("El negocio está cerrado en este momento")
        pedido = Pedido.objects.create(**data, cliente=usuario)
        producto.stock -= 1
        producto.save(update_fields=["stock", "actualizado_en"])
        return pedido
```

## **Ejemplo — Excepciones de Dominio** 

```
# exceptions.py
```

```
class AppError(Exception):
    """Base de todas las excepciones de la aplicación."""
```

```
class ReglaNegocioViolada(AppError): pass
class RecursoNoEncontrado(AppError): pass
class AccesoNoAutorizado(AppError): pass
```

```
# Específicas del dominio
class ProductoSinStock(ReglaNegocioViolada): pass
class NegocioCerrado(ReglaNegocioViolada): pass
class TransicionEstadoInvalida(ReglaNegocioViolada): pass
class CajaNoAbierta(ReglaNegocioViolada): pass
class AsientoNoDisponible(ReglaNegocioViolada): pass
```

## **Ejemplo — Modelo Base + Soft Delete** 

```
# utils/models.py
```

```
class ManagerActivos(models.Manager):
    def get_queryset(self): return super().get_queryset().filter(activo=True)
```

```
class ModeloBase(models.Model):
    creado_en      = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por     = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        related_name="+", on_delete=models.SET_NULL
    )
    activo = models.BooleanField(default=True, db_index=True)
    objects = models.Manager()   # todos los registros
```

```
    activos = ManagerActivos()   # solo activos
```

```
    def eliminar(self, usuario=None):
        """Soft delete: nunca borrar físicamente."""
        self.activo = False
        if usuario: self.creado_por = usuario
        self.save(update_fields=["activo", "actualizado_en"])
```

```
    class Meta:
        abstract = True
```

## **NIVEL 2 — Elegir 1 patrón según el proyecto (15% de la nota)** 

• Cada proyecto tiene un patrón recomendado en su ficha, pero el grupo puede elegir cualquiera de los 6. 

• Repository Pattern: abstrae el acceso a datos. El Service usa una interfaz, no el ORM directamente. 

• Strategy Pattern: reglas de negocio intercambiables (ej: políticas de descuento, políticas de cancelación). 

• Celery + tareas asíncronas: procesos no bloqueantes (TTL de reservas, envío de emails, reportes async). 

• Caché con Redis: reducir queries repetidas en buscadores y listados de alta frecuencia. 

• Eventos de Dominio: desacoplamiento entre módulos mediante publicación/suscripción de eventos. 

• WebSockets con Django Channels: actualizaciones en tiempo real (KDS de cocina, tracking, plano de hotel). 

## **Ejemplo — Repository Pattern** 

```
# dominio/puertos/repositorios.py
from typing import Protocol
```

```
class IEncomiendaRepository(Protocol):
    def obtener_por_codigo(self, codigo: str) -> "Encomienda": ...
    def listar_activas(self) -> list["Encomienda"]: ...
    def guardar(self, encomienda: "Encomienda") -> None: ...
```

```
# infraestructura/persistencia/encomienda_repo.py
class EncomiendaRepositoryDjango:
    def obtener_por_codigo(self, codigo: str):
        try:
            return EncomiendaModel.objects.select_related(
                "remitente", "agencia_origen"
            ).get(codigo=codigo, activo=True)
        except EncomiendaModel.DoesNotExist:
```

```
            raise RecursoNoEncontrado(f"Encomienda {codigo} no existe")
    def guardar(self, encomienda):
        encomienda.save()
# services.py — Service usa el puerto, no el ORM directamente
class EncomiendaService:
    def __init__(self, repo: IEncomiendaRepository):
        self.repo = repo
    def cambiar_estado(self, codigo: str, nuevo_estado: str) -> None:
        enc = self.repo.obtener_por_codigo(codigo)
        enc.cambiar_estado(nuevo_estado)  # lógica en la entidad
        self.repo.guardar(enc)
```

## **Ejemplo — Strategy Pattern** 

```
# strategies/reembolso.py
from typing import Protocol
from decimal import Decimal
class PoliticaReembolso(Protocol):
    def calcular(self, monto: Decimal, horas_anticipacion: int) -> Decimal: ...
class ReembolsoTotal:
    def calcular(self, monto, horas_anticipacion): return monto
class ReembolsoParcial:
    def calcular(self, monto, horas_anticipacion):
        return monto * Decimal("0.80") if horas_anticipacion >= 24 else
Decimal("0")
class SinReembolso:
    def calcular(self, monto, horas_anticipacion): return Decimal("0")
# service usa la estrategia — no sabe cuál es
class CancelacionService:
    def __init__(self, politica: PoliticaReembolso):
        self.politica = politica
    def cancelar(self, boleto) -> Decimal:
```

```
        horas = calcular_horas(boleto.viaje.fecha_salida)
        return self.politica.calcular(boleto.precio_final, horas)
```

## **Ejemplo — Celery (TTL de reservas)** 

```
# tasks.py
from celery import shared_task
```

```
@shared_task
def liberar_reserva_expirada(reserva_id: int):",
    from .models import Reserva
    try:
        r = Reserva.objects.get(pk=reserva_id, estado="PENDIENTE")
        r.asiento.estado = "DISPONIBLE"
        r.asiento.save(update_fields=["estado"])
        r.estado = "EXPIRADA"
        r.save(update_fields=["estado", "actualizado_en"])
    except Reserva.DoesNotExist:
        pass  # ya fue procesada (comprada o cancelada)
# services.py — lanza la tarea al crear la reserva
class ReservaService:
    @staticmethod
    @transaction.atomic
    def crear(viaje_id, asiento_id, pasajero) -> Reserva:
        # ... validaciones ...
        reserva = Reserva.objects.create(...)
        # Liberar en 15 minutos si no se confirma
        liberar_reserva_expirada.apply_async(
            args=[reserva.id], countdown=900
        )
        return reserva
```

## **Ejemplo — Eventos de Dominio** 

```
# events.py
from dataclasses import dataclass
from datetime import datetime
@dataclass
class PedidoEntregado:
    pedido_id: int
```

```
    cliente_email: str
    repartidor_id: int
    fecha: datetime
# event_bus.py
handlers = {}
```

```
def subscribe(event_class, handler): ...
def publish(event):
    for h in handlers.get(type(event), []):
        h(event)
# handlers/notificaciones.py — reacciona al evento
def al_entregar_pedido(event: PedidoEntregado):
    EmailService.enviar_confirmacion(event.cliente_email)
    EstadisticaService.registrar_entrega(event.repartidor_id)
```

```
# service — emite, no sabe quién escucha
class PedidoService:
    def entregar(self, pedido_id: int) -> None:
        pedido = self.repo.obtener(pedido_id)
        pedido.marcar_entregado()
        self.repo.guardar(pedido)
        publish(PedidoEntregado(
            pedido_id=pedido.id,
            cliente_email=pedido.cliente.email,
            repartidor_id=pedido.repartidor_id,
            fecha=datetime.now()
        ))
```

## **NIVEL 3 — Arquitectura Hexagonal (+10 puntos BONUS)** 

- El directorio dominio/ no puede tener ningún import de Django (ni models, ni settings, ni nada). 

- Entidades de dominio como dataclasses o clases Python puras con toda la lógica de negocio. 

- Puertos definidos como typing.Protocol. Adaptadores en infraestructura/ implementan los puertos. 

- Views de Django solo reciben el request y delegan al dominio. Son adaptadores de entrada. 

- Tests del dominio no usan base de datos — usan repositorios mock. 

- Estructura de carpetas: dominio/ — infraestructura/ — interfaces/ 

## **Estructura de carpetas — Arquitectura Hexagonal** 

```
proyecto/
```

```
├── dominio/                  ← Python puro. CERO Django.
│├── entidades/            ← Clases de dominio con lógica de negocio
││   └── pedido.py         ← dataclass + métodos de dominio
│├── servicios/            ← Casos de uso
││   └── pedido_service.py
│├── puertos/              ← Interfaces (Protocol)
││├── repositorios.py   ← IPedidoRepository, IClienteRepository
││   └── notificaciones.py ← IEmailService, ISMSService
│   └── excepciones.py
│
├── infraestructura/          ← Implementaciones concretas
│├── persistencia/         ← Adaptadores Django ORM
││   └── pedido_repo.py
│├── email/                ← Adaptador SMTP / SendGrid
│   └── cache/                ← Adaptador Redis
│
└── interfaces/               ← Adaptadores de entrada
├── api/
│├── views.py          ← Solo recibe request, llama al dominio
│   └── serializers.py
    └── admin.py
```

## **Entidad de dominio — Python puro** 

```
# dominio/entidades/pedido.py — SIN imports de Django
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from ..excepciones import TransicionEstadoInvalida
```

```
@dataclass
class Pedido:
    id: int | None
    cliente_id: int
    estado: str = "RECIBIDO"
    total: Decimal = Decimal("0")
    items: list = field(default_factory=list)
    TRANSICIONES = {
        "RECIBIDO":    ["CONFIRMADO", "CANCELADO"],
        "CONFIRMADO":  ["EN_PREPARACION", "CANCELADO"],
```

```
        "EN_PREPARACION": ["LISTO_PARA_RECOJO"],
        "LISTO_PARA_RECOJO": ["EN_CAMINO"],
        "EN_CAMINO":   ["ENTREGADO"],
    }
```

```
    def cambiar_estado(self, nuevo: str) -> None:
        if nuevo not in self.TRANSICIONES.get(self.estado, []):
            raise TransicionEstadoInvalida(
                f"No se puede ir de {self.estado} a {nuevo}"
            )
        self.estado = nuevo
```

PROYECTO 2 

## **Sistema de Punto de Venta (POS)** 

## **Descripción del Sistema** 

Gestión de ventas en el mostrador, control de inventario, apertura/cierre de caja y reportes. Orientado a negocios retail. 

## **Modelos de Datos Requeridos** 

## **Entidades:** 

- Producto: codigo_barra, nombre, categoria, precio_venta, costo, stock_actual, stock_minimo, unidad — ModeloBase 

- Proveedor: nombre, ruc, contacto — ModeloBase 

- Caja: nombre, saldo_inicial, saldo_final, fecha_apertura, fecha_cierre, cajero, 

- estado(ABIERTA/CERRADA) 

- MovimientoCaja: caja, tipo(INGRESO/EGRESO), monto, concepto, creado_en 

- Venta: cajero, caja, subtotal, descuento, igv, total, metodo_pago, estado(COMPLETADA/ANULADA) 

- DetalleVenta: venta, producto, cantidad, precio_unitario, subtotal 

- Compra: proveedor, total, estado — DetalleCompra: compra, producto, cantidad, costo_unitario 

## **Endpoints Mínimos** 

- POST /api/ventas/ — VentaService.registrar: valida caja abierta, descuenta stock, actualiza saldo 

- • POST /api/cajas/{id}/apertura/ — CajaService.abrir: registra saldo inicial 

- POST /api/cajas/{id}/cierre/ — CajaService.cerrar: calcula diferencia y cierra 

- GET /api/productos/buscar/?q= — Búsqueda por nombre o código de barra (con caché) 

- GET /api/reportes/ventas-del-dia/ — Total, por método de pago, top 5 productos 

- GET /api/reportes/stock-critico/ — Productos bajo stock mínimo 

- POST /api/compras/ — CompraService.registrar: entrada de mercadería, incrementa stock 

- GET /api/reportes/utilidad/?periodo= — Ingresos vs costos por periodo 

## **Vistas Web Requeridas** 

## **Vistas / Pantallas Web Requeridas  (Django Templates + Bootstrap 5  |  React/Vue)** 

- Pantalla de Venta: buscador de producto (nombre o código de barra), ticket en tiempo real con cantidades editables, total y botón Cobrar con selector de método de pago 

- Apertura de Caja: formulario de saldo inicial, historial de aperturas anteriores 

- Cierre de Caja: resumen automático del turno, diferencia calculada, confirmación 

- Inventario: tabla con paginación, búsqueda, filtro por categoría, fila roja si stock crítico, CRUD 

- Entrada de Mercadería: formulario con selección de proveedor y líneas de productos 

- Reportes — Ventas del Día: totales por método de pago, gráfico de top 5 productos 

- Reportes — Utilidad: ingresos vs costo por período en gráfico de barras 

- Dashboard Admin: ventas del día, caja actual, alertas de stock crítico, accesos directos 

## **Reglas de Negocio Críticas** 

- VentaService lanza CajaNoAbierta si no hay caja activa para el cajero 

- VentaService lanza ProductoSinStock si stock = 0 para algún ítem 

- Ventas no se eliminan físicamente — solo se anulan con motivo obligatorio 

- • precio_venta no puede ser menor al costo (MargenInvalidoError) • Saldo de cierre = saldo_inicial + sum(INGRESOS) - sum(EGRESOS) 

## **Requerimientos Arquitectónicos Específicos** 

• Nivel 1 (obligatorio): Service Layer, Excepciones de dominio, Soft Delete + auditoría, Docker Compose. 

• Nivel 2 recomendado: Strategy Pattern o Caché Redis — Strategy para políticas de descuento (cliente frecuente, descuento por volumen, precio especial). Caché Redis para la búsqueda de productos por código de barra (query más frecuente del sistema, misma respuesta para todos). 

• Nivel 3 (bonus +10 pts): Arquitectura Hexagonal — dominio/ sin imports de Django. 

## **Rúbrica de Evaluación** 

|**Área**|**Peso**|**Logrado 100%**|**En Progreso**<br>**70%**|**Básico 40%**|**Insuficiente 0%**|
|---|---|---|---|---|---|
|**Modelos y DB**<br>**10%**|**10%**|Todas las entidades|Entidades sin|Modelos básicos|Modelos<br>incompletos|
|||con ModeloBase,<br>constraint stock >= 0,<br>índice en codigo_barra|constraint de<br>stock o sin índice<br>en código de<br>barra|sin ModeloBase<br>ni constraints||
|**API REST**<br>**10%**|**10%**|Todos los endpoints|Endpoints|CRUD básico sin|< 50% de<br>endpoints|
|||con actualización<br>atómica de stock y<br>saldo de caja|principales sin<br>atomicidad|lógica de caja ni<br>stock||
|**Lógica — Caja**<br>**10%**|**10%**|VentaService valida|Service|Lógica de caja en|Sin módulo de caja|
|||caja abierta,<br>CajaService calcula<br>cuadre automático con<br>diferencia|implementado<br>pero validación<br>de caja parcial o<br>cuadre incorrecto|View sin Service||
|**Frontend Web**<br>**15%**|**15%**|Pantalla de venta|Venta y caja|Formularios|Sin frontend o<br>desconectado|
|||interactiva con<br>búsqueda en tiempo<br>real, ticket dinámico,<br>reportes con gráficas|<br>funcionales sin<br>búsqueda en<br>tiempo real ni<br>gráficas|básicos sin<br>experiencia de<br>caja||
|**Integración +**<br>**Auth**<br>**10%**|**10%**|JWT con roles (admin,|JWT con roles|Auth básica sin|Sin auth|
|||cajero, supervisor),<br>cajero no accede a<br>reportes de utilidad ni<br>compras|pero rutas no<br>protegidas|roles||
|**Nivel 1 —**<br>**Service Layer**<br>**+ Excepciones**<br>**15%**|**15%**|Service por módulo con|Service|Función de|Sin capa de<br>servicios. Toda la<br>lógica en Views o<br>Serializers|
|||toda la lógica de<br>negocio. Excepciones<br>de dominio propias<br>capturadas en Views<br>con handlers<br>específicos. Views sin<br>lógica de negocio|implementado<br>pero Views aún<br>contienen lógica.<br>Excepciones<br>parciales o<br>usando<br>ValueError<br>genérico|servicio sin clase,<br>lógica mezclada<br>con serializers o<br>views||
|**Nivel 1 — Soft**<br>**Delete +**<br>**Docker**<br>**10%**|**10%**|Modelo base abstracto|Modelo base|Campos de|Sin auditoría ni soft<br>delete. Sin Docker|
|||con creado_en,<br>actualizado_en,<br>creado_por, activo.|presente pero sin<br>creado_por o sin<br>soft delete.|auditoría en<br>algunos modelos<br>pero sin modelo||



|||Soft delete<br>implementado. Docker<br>Compose funcional:<br>levantar con un<br>comando|Docker Compose<br>parcial (falta<br>PostgreSQL o<br>variables de<br>entorno)|base abstracto.<br>Solo Dockerfile<br>sin Compose||
|---|---|---|---|---|---|
|**Nivel 2 —**<br>**Strategy**<br>**(descuentos) o**<br>**Caché Redis**<br>**(búsqueda de**<br>**productos)**<br>**15%**|**15%**|Patrón implementado|Patrón|Intento de|Patrón no<br>implementado o<br>implementado de<br>forma que no<br>aporta<br>desacoplamiento|
|||correctamente,<br>integrado al flujo<br>principal, con tests que<br>demuestran el<br>beneficio del<br>desacoplamiento|implementado<br>pero sin tests que<br>lo validen o<br>integración<br>incompleta|implementar el<br>patrón pero con<br>errores de diseño<br>(dependencias<br>circulares,<br>acoplamiento)||
|**Testing**<br>**5%**|**5%**|Tests de flujo principal,|Tests principales,|Tests básicos,|Sin tests|
|||lógica crítica y<br>permisos. Cobertura ≥<br>60%|cobertura 40-60%|cobertura < 40%||
|**Docs y Calidad**<br>**5%**|**5%**|Swagger completo,|Swagger|Solo README|Sin documentación|
|||README con setup<br>frontend+backend, sin<br>N+1 en queries|generado y<br>README básico|||



