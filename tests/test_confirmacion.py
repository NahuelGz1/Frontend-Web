import unittest
from html.parser import HTMLParser

from flask import render_template, request

from helpers import Formulario, PruebaPlantillas


class Imagenes(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.imagenes = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.imagenes.append(dict(attrs))


class ConfirmacionTest(PruebaPlantillas):
    def datos_confirmacion(self):
        return {
            "funcion": self.funcion(),
            "resumen": {
                "butacas": [{"fila": "D", "numero": 5}, {"fila": "D", "numero": 6}],
                "subtotal_entradas": "$ 20.000",
                "servicios": [
                    {"nombre": "Combo duo", "cantidad": 1, "subtotal": "$ 8.500"},
                    {"nombre": "Nachos con cheddar", "cantidad": 1, "subtotal": "$ 4.000"},
                ],
                "subtotal_servicios": "$ 12.500",
                "total": "$ 32.500 ARS",
            },
            "reserva": {
                "id": "reserva-42",
                "codigo": "CP-261030-0842",
                "estado": "confirmada",
                "cancelacion_permitida": True,
                "mensaje_cancelacion": "Cancelacion habilitada por la API hasta el plazo indicado en tu reserva.",
                "entradas": [
                    {
                        "fila": "D", "numero": numero,
                        "codigo": f"CP-261030-0842-D{numero}",
                        "qr_url": f"/reservas/reserva-42/entradas/D{numero}/qr",
                    }
                    for numero in (5, 6)
                ],
            },
            "csrf_token": "token-exclusivo-de-prueba",
            "error_confirmacion": None,
            "error_cancelacion": None,
        }

    def renderizar(self, plantilla="cliente/confirmacion.html", **cambios):
        contexto = self.datos_confirmacion()
        contexto.update(cambios)
        with self.app.test_request_context():
            return render_template(plantilla, **contexto)

    def test_detalle_final_y_qr_individuales_del_servidor(self):
        html = self.renderizar()
        for texto in (
            "¡Tu compra fue exitosa!", "Pago aprobado", "CP-261030-0842",
            "Volver al Futuro", "Sala 1", "Fila D · Butaca 5", "Fila D · Butaca 6",
            "2 entradas", "$ 20.000", "1 × Combo duo", "1 × Nachos con cheddar",
            "$ 12.500", "Total pagado", "$ 32.500 ARS", "Entrada 1 de 2", "Entrada 2 de 2",
        ):
            with self.subTest(texto=texto):
                self.assertIn(texto, html)
        self.assertNotIn("Total calculado", html)
        imagenes = Imagenes(html).imagenes
        qr = [img for img in imagenes if img["src"].endswith("/qr")]
        self.assertEqual(len(qr), 2)
        self.assertEqual(
            [img["src"] for img in qr],
            [e["qr_url"] for e in self.datos_confirmacion()["reserva"]["entradas"]],
        )
        self.assertTrue(all(i["width"] == "148" and i["height"] == "148" for i in qr))
        self.assertIn("butaca 5", qr[0]["alt"])
        self.assertEqual(html.count("<main "), 1)

    def test_cancelacion_es_post_con_csrf_sin_permisos_ni_totales(self):
        html = self.renderizar()
        formulario = Formulario(html)
        self.assertEqual(len(formulario.formularios), 1)
        form = formulario.formularios[0]
        self.assertEqual(form["method"].upper(), "POST")
        self.assertEqual(form["action"], "/reservas/reserva-42/cancelar")
        boton = formulario.botones[0]
        self.assertEqual(boton["type"], "submit")
        datos = {i["name"]: i["value"] for i in formulario.inputs}
        datos[boton["name"]] = boton["value"]
        self.assertEqual(datos, {
            "csrf_token": "token-exclusivo-de-prueba", "accion": "cancelar",
        })
        recibidos = {}

        def recibir(reserva_id):
            recibidos.update(reserva_id=reserva_id, datos=request.form.to_dict())
            return "Solicitud recibida por la ruta de prueba"

        self.app.view_functions["cliente.cancelar_reserva"] = recibir
        with self.app.test_client() as client:
            respuesta = client.post(form["action"], data=datos)
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(client.get(form["action"]).status_code, 405)
        self.assertEqual(recibidos, {"reserva_id": "reserva-42", "datos": datos})

    def test_permiso_de_api_falso_oculta_formulario_sin_ocultar_entradas(self):
        datos = self.datos_confirmacion()
        datos["reserva"].update(
            cancelacion_permitida=False,
            mensaje_cancelacion="El plazo permitido ya vencio.",
        )
        html = self.renderizar(**datos)
        self.assertIn("El plazo permitido ya vencio.", html)
        self.assertFalse(Formulario(html).formularios)
        self.assertNotIn("/reservas/reserva-42/cancelar", html)
        self.assertIn("/reservas/reserva-42/entradas/D5/qr", html)

    def test_no_confirma_pago_ni_muestra_qr_en_estados_no_confirmados(self):
        for estado in ("pendiente", "rechazada", "cancelada", "desconocida"):
            with self.subTest(estado=estado):
                datos = self.datos_confirmacion()
                datos["reserva"]["estado"] = estado
                html = self.renderizar(**datos)
                self.assertNotIn("¡Tu compra fue exitosa!", html)
                self.assertNotIn("Pago aprobado", html)
                self.assertFalse(Imagenes(html).imagenes)
                self.assertFalse(Formulario(html).formularios)
                self.assertNotIn("Total pagado", html)
                if estado == "cancelada":
                    self.assertIn("Reserva cancelada", html)

    def test_error_de_consulta_y_reserva_ausente_no_exponen_datos_previos(self):
        for cambios in (
            {"error_confirmacion": "No se pudo consultar la API."},
            {"error_confirmacion": "No se pudo consultar la API.", "reserva": None},
            {"reserva": None},
        ):
            with self.subTest(cambios=cambios):
                html = self.renderizar(**cambios)
                self.assertNotIn("CP-261030-0842", html)
                self.assertNotIn("Volver al Futuro", html)
                self.assertFalse(Imagenes(html).imagenes)
                self.assertFalse(Formulario(html).formularios)

    def test_qr_faltante_y_entradas_vacias_muestran_error_sin_reemplazos(self):
        datos = self.datos_confirmacion()
        datos["reserva"]["entradas"][0]["qr_url"] = None
        html = self.renderizar(**datos)
        self.assertIn("El código QR de esta entrada no está disponible", html)
        self.assertEqual(html.count('class="confirmacion-qr"'), 1)
        self.assertIn('role="alert"', html)
        datos["reserva"]["entradas"] = []
        html = self.renderizar(**datos)
        self.assertIn("No se recibieron las entradas digitales", html)
        self.assertNotIn('class="confirmacion-qr"', html)

    def test_fallo_de_cancelacion_no_simula_exito(self):
        datos = self.datos_confirmacion()
        datos["reserva"]["cancelacion_permitida"] = False
        datos["error_cancelacion"] = "La API rechazo la cancelacion porque vencio el plazo."
        html = self.renderizar(**datos)
        self.assertIn(datos["error_cancelacion"], html)
        self.assertIn('role="alert"', html)
        self.assertNotIn("Reserva cancelada", html)
        self.assertIn("/reservas/reserva-42/entradas/D5/qr", html)
        self.assertFalse(Formulario(html).formularios)

    def test_escapa_referencias_y_mensajes_del_servidor(self):
        datos = self.datos_confirmacion()
        texto = '<script>alert("prueba")</script>'
        datos["reserva"]["codigo"] = texto
        datos["reserva"]["entradas"][0]["codigo"] = texto
        datos["error_cancelacion"] = texto
        html = self.renderizar(**datos)
        self.assertNotIn(texto, html)
        self.assertIn("&lt;script&gt;", html)

    def test_iconos_locales_y_plantilla_anterior(self):
        self.assertEqual(self.renderizar(), self.renderizar(plantilla="cliente/compra-exitosa.html"))
        with self.app.test_client() as client:
            for imagen in ("confirmacion-check.svg", "confirmacion-check-movil.svg"):
                with self.subTest(imagen=imagen):
                    with client.get(f"/static/images/{imagen}") as respuesta:
                        self.assertEqual(respuesta.status_code, 200)
                        self.assertTrue(respuesta.data)


if __name__ == "__main__":
    unittest.main()
