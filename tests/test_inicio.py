import unittest

from flask import render_template

from helpers import PruebaPlantillas


class InicioTest(PruebaPlantillas):
    def renderizar(self):
        with self.app.test_request_context():
            return render_template("cliente/inicio.html")

    def test_pagina_usa_layout_compartido_y_tiene_navegacion_activa(self):
        html = self.renderizar()
        self.assertIn("<title>Inicio · Cine Paradiso</title>", html)
        self.assertEqual(html.count("<main "), 1)
        self.assertIn('class="is-active" aria-current="page">Inicio</a>', html)
        self.assertIn('class="site-footer"', html)

    def test_muestra_los_cinco_servicios_del_mockup(self):
        html = self.renderizar()
        for servicio in ("Bebidas", "Pochoclos", "Snacks", "Estacionamiento", "Acceso VIP"):
            with self.subTest(servicio=servicio):
                self.assertIn(f"<h3>{servicio}</h3>", html)
        self.assertEqual(html.count('class="service-card"'), 5)

    def test_conserva_secciones_del_mockup_sin_imagenes_rotas(self):
        html = self.renderizar()
        for seccion in ("Volver al Futuro", "Hoy en Paradiso", "Próximos estrenos"):
            with self.subTest(seccion=seccion):
                self.assertIn(seccion, html)
        self.assertNotIn("<img", html)
        self.assertIn('role="img"', html)
        self.assertIn("/static/css/cine-paradiso.css", html)


if __name__ == "__main__":
    unittest.main()
