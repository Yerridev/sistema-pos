from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.exceptions import CajaAjena, CajaNoAbierta, CajaYaAbierta, ReglaNegocioViolada
from .models import Caja, MovimientoCaja


class CajaService:
    """Servicio de dominio para operaciones de caja.

    Es la única fuente de verdad para abrir, cerrar y registrar movimientos
    de caja; las views actúan únicamente como adaptadores delegando aquí.
    """

    @classmethod
    @transaction.atomic
    def abrir(cls, usuario, nombre, saldo_inicial):
        """Crea una nueva caja ABIERTA para el usuario.

        Args:
            usuario: instancia de ``Usuario`` que abre la caja.
            nombre: nombre descriptivo de la caja.
            saldo_inicial: saldo con el que inicia la caja (Decimal).

        Raises:
            CajaYaAbierta: si el usuario ya tiene otra caja ABIERTA.
        """
        if Caja.objects.filter(cajero=usuario, estado='ABIERTA').exists():
            raise CajaYaAbierta("Ya existe una caja ABIERTA para este cajero.")

        return Caja.objects.create(
            nombre=nombre,
            saldo_inicial=saldo_inicial,
            cajero=usuario,
            estado='ABIERTA',
            creado_por=usuario,
        )

    @classmethod
    @transaction.atomic
    def abrir_caja_existente(cls, caja, usuario, saldo_inicial):
        """Reabre una caja existente que esté CERRADA.

        Este método atiende el endpoint API ``/api/cajas/{id}/abrir/`` que
        opera sobre un recurso existente, a diferencia de ``abrir()`` que
        crea una caja nueva.

        Args:
            caja: instancia de ``Caja`` a reabrir.
            usuario: usuario que realiza la operación.
            saldo_inicial: nuevo saldo inicial a establecer.

        Raises:
            CajaAjena: si la caja pertenece a otro usuario y no es admin.
            CajaYaAbierta: si ya existe otra caja ABIERTA para el usuario,
                o si la caja objetivo ya está ABIERTA.
        """
        if caja.cajero_id != usuario.id and getattr(usuario, 'rol', None) != 'admin':
            raise CajaAjena("No puede abrir una caja de otro cajero.")
        if Caja.objects.filter(cajero=usuario, estado='ABIERTA').exclude(pk=caja.pk).exists():
            raise CajaYaAbierta("Ya existe una caja ABIERTA para este cajero.")
        if caja.estado == 'ABIERTA':
            raise CajaYaAbierta("La caja ya está ABIERTA.")

        caja.saldo_inicial = Decimal(str(saldo_inicial))
        caja.fecha_apertura = timezone.now()
        caja.fecha_cierre = None
        caja.saldo_final = None
        caja.estado = 'ABIERTA'
        caja.cajero = usuario
        caja.save(update_fields=[
            'saldo_inicial', 'fecha_apertura', 'fecha_cierre',
            'saldo_final', 'estado', 'cajero',
        ])
        return caja

    @classmethod
    @transaction.atomic
    def cerrar(cls, caja, usuario):
        """Cierra una caja ABIERTA registrando su saldo final.

        Args:
            caja: instancia de ``Caja`` a cerrar.
            usuario: usuario que realiza el cierre.

        Raises:
            ReglaNegocioViolada: si la caja no está ABIERTA.
            CajaAjena: si la caja pertenece a otro usuario y no es admin.
        """
        if caja.estado != 'ABIERTA':
            raise ReglaNegocioViolada("Solo se puede cerrar una caja ABIERTA.")
        if caja.cajero_id != usuario.id and getattr(usuario, 'rol', None) != 'admin':
            raise CajaAjena("No puede cerrar una caja de otro cajero.")

        caja.saldo_final = caja.saldo_actual
        caja.fecha_cierre = timezone.now()
        caja.estado = 'CERRADA'
        caja.save(update_fields=['saldo_final', 'fecha_cierre', 'estado'])
        return caja

    @classmethod
    @transaction.atomic
    def registrar_movimiento(cls, caja, usuario, tipo, monto, concepto):
        """Registra un movimiento de ingreso o egreso en una caja abierta.

        Args:
            caja: instancia de ``Caja`` donde se registra el movimiento.
            usuario: usuario que registra el movimiento.
            tipo: ``INGRESO`` o ``EGRESO``.
            monto: importe del movimiento (Decimal).
            concepto: descripción del movimiento.

        Raises:
            CajaNoAbierta: si la caja no está ABIERTA.
            CajaAjena: si la caja pertenece a otro usuario y no es admin.
            ReglaNegocioViolada: si el tipo es inválido o el monto no es
                mayor que cero.
        """
        if caja.estado != 'ABIERTA':
            raise CajaNoAbierta("Solo se registran movimientos en cajas abiertas.")
        if caja.cajero_id != usuario.id and getattr(usuario, 'rol', None) != 'admin':
            raise CajaAjena("No puedes registrar movimientos en esta caja.")
        if tipo not in {'INGRESO', 'EGRESO'}:
            raise ReglaNegocioViolada("Selecciona un tipo de movimiento válido.")
        if monto <= 0:
            raise ReglaNegocioViolada("El monto debe ser mayor que cero.")

        return MovimientoCaja.objects.create(
            caja=caja,
            tipo=tipo,
            monto=monto,
            concepto=concepto,
            usuario=usuario,
        )
