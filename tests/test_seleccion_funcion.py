import unittest
from html.parser import HTMLParser

from flask import render_template, url_for

from helpers import PruebaPlantillas


class Enlaces(HTMLParser):
    def __init__(self):
        super().__init__()
        self.destinos = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.destinos.append(dict(attrs).get("href"))


class SeleccionFuncionTest(PruebaPlantillas):
    def renderizar(self, funciones, error=None):
        with self.app.test_request_context():
            return render_template(
                "cliente/seleccion_funcion.html",
                funciones=funciones,
                error_funciones=error,
            )

    def enlaces(self, html):
        parser = Enlaces()
        parser.feed(html)
        return parser.destinos

    def test_muestra_datos_y_enlaces_de_cada_funcion(self):
        html = self.renderizar([
            self.funcion(),
            self.funcion(
                43, pelicula={"titulo": "Cinema Paradiso"},
                horario="21:45", sala={"nombre": "Sala 2"},
            ),
        ])
        for texto in (
            "Volver al Futuro", "Cinema Paradiso", "Sala 1", "Sala 2",
            '<time datetime="2026-10-30">2026-10-30</time>',
            'datetime="19:30">19:30</time>',
            'datetime="21:45">21:45</time>',
        ):
            with self.subTest(texto=texto):
                self.assertIn(texto, html)
        self.assertIn("/funciones/42/butacas", self.enlaces(html))
        self.assertIn("/funciones/43/butacas", self.enlaces(html))
        self.assertEqual(html.count('<article class="compra-funcion"'), 2)

    def test_lista_vacia_no_inventa_funciones(self):
        html = self.renderizar([])
        self.assertIn("No hay funciones disponibles", html)
        self.assertNotIn('<article class="compra-funcion"', html)
        self.assertNotIn("Elegir butacas</a>", html)

    def test_funcion_agotada_no_ofrece_navegacion(self):
        html = self.renderizar([self.funcion(disponible=False)])
        self.assertIn("Función sin disponibilidad", html)
        self.assertIn("Volver al Futuro", html)
        self.assertNotIn("/funciones/42/butacas", self.enlaces(html))

    def test_error_no_muestra_datos_previos_ni_estado_vacio(self):
        html = self.renderizar([self.funcion()], "Intentalo nuevamente.")
        self.assertIn('role="alert"', html)
        self.assertIn("Intentalo nuevamente.", html)
        self.assertNotIn("Volver al Futuro", html)
        self.assertNotIn("No hay funciones disponibles", html)
        self.assertIn("/cartelera", self.enlaces(html))

    def test_escapa_textos_y_atributos(self):
        texto = '<script>alert("prueba")</script>'
        html = self.renderizar([
            self.funcion(pelicula={"titulo": texto}, sala={"nombre": texto}),
        ])
        self.assertNotIn(texto, html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn(texto, self.renderizar([], texto))

    def test_layout_estilos_icono_y_paso_actual(self):
        html = self.renderizar([self.funcion()])
        self.assertEqual(html.count("<main "), 1)
        self.assertEqual(html.count("<h1 "), 1)
        self.assertIn('aria-current="step"', html)
        self.assertIn("/static/css/compra.css", html)
        self.assertIn("/static/images/compra-volver.svg", html)
        self.assertIn('alt="" width="16" height="16"', html)
        with self.app.test_client() as client:
            for recurso in ("css/compra.css", "images/compra-volver.svg"):
                with self.subTest(recurso=recurso):
                    with client.get(f"/static/{recurso}") as respuesta:
                        self.assertEqual(respuesta.status_code, 200)
                        self.assertTrue(respuesta.data)

    def test_identificador_se_conserva_en_la_url_del_siguiente_paso(self):
        html = self.renderizar([self.funcion(123)])
        with self.app.test_request_context():
            destino = url_for("cliente.elegir_butacas", funcion_id=123)
        self.assertIn(destino, self.enlaces(html))
        adaptador = self.app.url_map.bind("localhost")
        endpoint, valores = adaptador.match(destino, method="GET")
        self.assertEqual(endpoint, "cliente.elegir_butacas")
        self.assertEqual(valores, {"funcion_id": 123})


if __name__ == "__main__":
    unittest.main()
