"""Tests del Strategy Pattern de políticas de descuento.

Son ``SimpleTestCase`` porque las políticas son lógica pura de dominio y no
tocan la base de datos.
"""

from decimal import Decimal

from django.test import SimpleTestCase

from core.descuentos import (
    DescuentoClienteFrecuente,
    DescuentoFijo,
    DescuentoPorVolumen,
    DescuentoPorcentaje,
    PrecioEspecial,
    obtener_politica,
)


class DescuentoFijoTest(SimpleTestCase):
    def test_descuento_fijo(self):
        d = DescuentoFijo()
        self.assertEqual(
            d.calcular(Decimal("100"), {"descuento_fijo": Decimal("10")}),
            Decimal("10"),
        )

    def test_no_supera_subtotal(self):
        d = DescuentoFijo()
        self.assertEqual(
            d.calcular(Decimal("50"), {"descuento_fijo": Decimal("100")}),
            Decimal("50"),
        )

    def test_negativo_se_ignora(self):
        d = DescuentoFijo()
        self.assertEqual(
            d.calcular(Decimal("100"), {"descuento_fijo": Decimal("-20")}),
            Decimal("0.00"),
        )

    def test_sin_contexto(self):
        d = DescuentoFijo()
        self.assertEqual(d.calcular(Decimal("100"), {}), Decimal("0.00"))


class DescuentoPorcentajeTest(SimpleTestCase):
    def test_10_por_ciento(self):
        d = DescuentoPorcentaje()
        self.assertEqual(
            d.calcular(Decimal("200"), {"porcentaje": Decimal("10")}),
            Decimal("20.00"),
        )

    def test_porcentaje_fuera_de_rango(self):
        d = DescuentoPorcentaje()
        self.assertEqual(d.calcular(Decimal("200"), {"porcentaje": Decimal("0")}), Decimal("0.00"))
        self.assertEqual(d.calcular(Decimal("200"), {"porcentaje": Decimal("150")}), Decimal("0.00"))


class DescuentoClienteFrecuenteTest(SimpleTestCase):
    def test_es_frecuente(self):
        d = DescuentoClienteFrecuente()
        self.assertEqual(
            d.calcular(Decimal("100"), {"es_cliente_frecuente": True}),
            Decimal("5.00"),
        )

    def test_no_es_frecuente(self):
        d = DescuentoClienteFrecuente()
        self.assertEqual(
            d.calcular(Decimal("100"), {"es_cliente_frecuente": False}),
            Decimal("0.00"),
        )


class DescuentoPorVolumenTest(SimpleTestCase):
    def test_mas_de_100_unidades(self):
        d = DescuentoPorVolumen()
        self.assertEqual(d.calcular(Decimal("1000"), {"cantidad_total": 150}), Decimal("150.00"))

    def test_entre_50_y_99(self):
        d = DescuentoPorVolumen()
        self.assertEqual(d.calcular(Decimal("1000"), {"cantidad_total": 60}), Decimal("100.00"))

    def test_entre_20_y_49(self):
        d = DescuentoPorVolumen()
        self.assertEqual(d.calcular(Decimal("1000"), {"cantidad_total": 30}), Decimal("50.00"))

    def test_menos_de_20(self):
        d = DescuentoPorVolumen()
        self.assertEqual(d.calcular(Decimal("100"), {"cantidad_total": 10}), Decimal("0.00"))


class PrecioEspecialTest(SimpleTestCase):
    def test_precio_especial_menor(self):
        d = PrecioEspecial()
        self.assertEqual(
            d.calcular(Decimal("100"), {"precio_especial_total": Decimal("80")}),
            Decimal("20.00"),
        )

    def test_precio_especial_mayor_o_igual_no_descuenta(self):
        d = PrecioEspecial()
        self.assertEqual(
            d.calcular(Decimal("100"), {"precio_especial_total": Decimal("120")}),
            Decimal("0.00"),
        )


class ObtenerPoliticaTest(SimpleTestCase):
    def test_politica_valida(self):
        self.assertIsInstance(obtener_politica("fijo"), DescuentoFijo)
        self.assertIsInstance(obtener_politica("porcentaje"), DescuentoPorcentaje)
        self.assertIsInstance(obtener_politica("volumen"), DescuentoPorVolumen)

    def test_politica_invalida(self):
        with self.assertRaises(ValueError):
            obtener_politica("no_existe")
