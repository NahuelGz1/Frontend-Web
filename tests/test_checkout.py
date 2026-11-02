import unittest

from flask import render_template, request

from helpers import Formulario, PruebaPlantillas


class CheckoutTest(PruebaPlantillas):
    def datos_checkout(self):
        def servicio(identificador, nombre, precio, maximo, cantidad=0):
            return {
                "id": identificador,
                "nombre": nombre,
                "precio_unitario": precio,
                "cantidad": cantidad,
                "maximo": maximo,
                "disponible": True,
                "error": None,
            }

        return {
            "funcion": self.funcion(),
            "resumen": {
                "butacas": [{"fila": "D", "numero": 5}, {"fila": "D", "numero": 6}],
                "subtotal_entradas": "$ 20.000",
                "servicios": [{"nombre": "Combo duo", "cantidad": 1, "subtotal": "$ 8.500"}],
                "subtotal_servicios": "$ 8.500",
                "total": "$ 28.500",
            },
            "servicios": {
                "combos": [servicio("combo-duo", "Combo duo", "$ 8.500", 4, 1)],
                "bebidas": [servicio("gaseosa", "Gaseosa", "$ 2.000", 6)],
                "estacionamiento": [servicio("cochera", "Cochera cubierta", "$ 3.000", 1)],
                "vip": [servicio("vip", "Pase VIP", "$ 5.000", 2)],
            },
            "csrf_token": "token-exclusivo-de-prueba",
            "error_checkout": None,
            "error_formulario": None,
        }

    def renderizar(self, **cambios):
        contexto = self.datos_checkout()
        contexto.update(cambios)
        with self.app.test_request_context():
            return render_template("cliente/checkout.html", **contexto)

    def test_resumen_muestra_entradas_asientos_y_total_del_servidor(self):
        html = self.renderizar()
        for texto in (
            "Volver al Futuro", "Sala 1", "Fila D · Butaca 5",
            "Fila D · Butaca 6", "2 entradas", "$ 20.000",
            "1 × Combo duo", "$ 8.500", "$ 28.500", "Total calculado",
            "último cálculo del servidor",
        ):
            with self.subTest(texto=texto):
                self.assertIn(texto, html)
        self.assertIn("/funciones/42/butacas", html)
        self.assertIn("/static/css/compra.css", html)
        self.assertEqual(html.count("<main "), 1)

    def test_cuatro_categorias_con_controles_nativos_y_etiquetas(self):
        html = self.renderizar()
        formulario = Formulario(html)
        numericos = [i for i in formulario.inputs if i["type"] == "number"]
        self.assertEqual(len(numericos), 2)
        self.assertEqual(len(formulario.selects), 2)
        for campo in numericos:
            self.assertEqual(campo["min"], "0")
            self.assertEqual(campo["step"], "1")
            self.assertIn("max", campo)
            self.assertIn("required", campo)
        controles = numericos + formulario.selects
        self.assertEqual(
            {c["id"] for c in controles},
            {label["for"] for label in formulario.labels},
        )
        self.assertEqual(len({c["name"] for c in controles}), 4)
        for titulo in ("Combos de comida", "Bebidas", "Estacionamiento", "Pase VIP"):
            self.assertIn(titulo, html)

    def test_cantidades_preservadas_y_limites_dados_por_api(self):
        datos = self.datos_checkout()
        datos["servicios"]["bebidas"][0]["cantidad"] = 3
        datos["servicios"]["vip"][0]["cantidad"] = 2
        datos["servicios"]["vip"][0]["maximo"] = 3
        formulario = Formulario(self.renderizar(**datos))
        bebida = next(i for i in formulario.inputs if i.get("name") == "servicio_gaseosa")
        self.assertEqual(bebida["value"], "3")
        vip = next(s for s in formulario.selects if s["name"] == "servicio_vip")
        self.assertEqual([o["value"] for o in vip["opciones"]], ["0", "1", "2", "3"])
        self.assertEqual([o["value"] for o in vip["opciones"] if "selected" in o], ["2"])

    def test_servicios_sin_stock_no_se_envian_y_se_muestran_en_cero(self):
        datos = self.datos_checkout()
        datos["servicios"]["combos"][0]["disponible"] = False
        datos["servicios"]["vip"][0]["maximo"] = 0
        formulario = Formulario(self.renderizar(**datos))
        combo = next(i for i in formulario.inputs if i.get("name") == "servicio_combo-duo")
        vip = next(s for s in formulario.selects if s["name"] == "servicio_vip")
        self.assertIn("disabled", combo)
        self.assertEqual(combo["value"], "0")
        self.assertIn("disabled", vip)
        self.assertEqual([o["value"] for o in vip["opciones"]], ["0"])

    def test_catalogo_vacio_permite_comprar_solo_entradas(self):
        datos = self.datos_checkout()
        datos["servicios"] = {clave: [] for clave in datos["servicios"]}
        datos["resumen"].update(
            servicios=[], subtotal_servicios="$ 0", total="$ 20.000"
        )
        html = self.renderizar(**datos)
        formulario = Formulario(html)
        self.assertEqual(html.count("No hay servicios disponibles en esta categoría."), 4)
        self.assertIn("Sin servicios adicionales.", html)
        self.assertEqual(len(formulario.formularios), 1)
        self.assertTrue(all("disabled" not in b for b in formulario.botones))

    def test_error_fatal_y_falta_de_butacas_no_ofrecen_checkout(self):
        datos = self.datos_checkout()
        datos["resumen"]["butacas"] = []
        for cambios, mensaje in (
            (datos, "Primero elegí tus butacas"),
            ({"error_checkout": "API no disponible.", "resumen": None, "servicios": None},
             "No pudimos cargar el checkout"),
        ):
            with self.subTest(mensaje=mensaje):
                html = self.renderizar(**cambios)
                self.assertIn(mensaje, html)
                self.assertFalse(Formulario(html).formularios)
                self.assertNotIn("$ 28.500", html)

    def test_error_de_campo_asociado_y_textos_escapados(self):
        datos = self.datos_checkout()
        texto = '<script>alert("prueba")</script>'
        datos["servicios"]["combos"][0].update(nombre=texto, error=texto)
        datos["error_formulario"] = texto
        html = self.renderizar(**datos)
        self.assertNotIn(texto, html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn('role="alert"', html)
        combo = next(i for i in Formulario(html).inputs if i.get("name") == "servicio_combo-duo")
        self.assertEqual(combo["aria-invalid"], "true")
        self.assertIn("servicio-combo-duo-error", combo["aria-describedby"])
        self.assertEqual(combo["value"], "1")

    def test_poster_dinamico_opcional_y_entrada_singular(self):
        datos = self.datos_checkout()
        self.assertNotIn('class="checkout-poster"', self.renderizar(**datos))
        datos["funcion"]["pelicula"]["poster_url"] = "/static/images/poster-prueba.png"
        datos["resumen"]["butacas"] = [{"fila": "A", "numero": 1}]
        html = self.renderizar(**datos)
        self.assertIn('src="/static/images/poster-prueba.png"', html)
        self.assertIn('alt="" width="96" height="120"', html)
        self.assertIn("1 entrada", html)
        self.assertNotIn("1 entradas", html)

    def test_post_de_acciones_envia_cantidades_y_no_importes(self):
        formulario = Formulario(self.renderizar())
        form = formulario.formularios[0]
        self.assertEqual(form["method"].upper(), "POST")
        self.assertEqual(form["action"], "/funciones/42/checkout")
        datos = {
            i["name"]: i["value"]
            for i in formulario.inputs
            if "disabled" not in i
        }
        for select in formulario.selects:
            datos[select["name"]] = next(
                o["value"] for o in select["opciones"] if "selected" in o
            )
        self.assertEqual(set(datos), {
            "csrf_token", "servicio_combo-duo", "servicio_gaseosa",
            "servicio_cochera", "servicio_vip",
        })
        recibidos = []

        def recibir(funcion_id):
            recibidos.append((funcion_id, request.form.to_dict()))
            return "Solicitud recibida por la ruta de prueba"

        self.app.view_functions["cliente.checkout"] = recibir
        with self.app.test_client() as client:
            for boton in formulario.botones:
                with self.subTest(accion=boton["value"]):
                    respuesta = client.post(
                        form["action"], data={**datos, boton["name"]: boton["value"]}
                    )
                    self.assertEqual(respuesta.status_code, 200)
        self.assertEqual([r[1]["accion"] for r in recibidos], ["actualizar", "continuar"])
        self.assertTrue(all(r[0] == 42 for r in recibidos))
        self.assertTrue(all(r[1]["servicio_combo-duo"] == "1" for r in recibidos))


if __name__ == "__main__":
    unittest.main()
