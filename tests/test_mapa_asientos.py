import unittest

from flask import render_template, request
from werkzeug.datastructures import MultiDict

from helpers import Formulario, PruebaPlantillas


class MapaAsientosTest(PruebaPlantillas):
    def filas(self):
        ocupadas = {
            "A3", "A4", "B6", "B7", "C2", "C9", "E5",
            "E6", "F7", "G3", "G4", "H9", "H10",
        }
        return [
            {
                "nombre": fila,
                "butacas": [
                    {
                        "id": f"{fila}{numero}",
                        "numero": numero,
                        "ocupada": f"{fila}{numero}" in ocupadas,
                    }
                    for numero in range(1, 11)
                ],
            }
            for fila in "ABCDEFGH"
        ]

    def renderizar(self, plantilla="cliente/mapa_asientos.html", **cambios):
        contexto = {
            "funcion": self.funcion(),
            "filas": self.filas(),
            "seleccionadas": [],
            "csrf_token": "token-exclusivo-de-prueba",
            "error_mapa": None,
            "error_seleccion": None,
        }
        contexto.update(cambios)
        with self.app.test_request_context():
            return render_template(plantilla, **contexto)

    def test_plano_del_diseno_y_etiquetas_asociadas(self):
        html = self.renderizar(seleccionadas=["D5", "D6"])
        formulario = Formulario(html)
        butacas = [i for i in formulario.inputs if i.get("name") == "butacas"]
        self.assertEqual(len(butacas), 80)
        self.assertEqual(sum("disabled" in i for i in butacas), 13)
        self.assertEqual({i["value"] for i in butacas if "checked" in i}, {"D5", "D6"})
        self.assertTrue(all(i["type"] == "checkbox" for i in butacas))
        ids = {i["id"] for i in butacas}
        self.assertEqual(len(ids), 80)
        self.assertEqual(ids, {label["for"] for label in formulario.labels})
        for texto in ("Pantalla", "Libre", "Ocupada", "Seleccionada", "Fila D, butaca 5"):
            self.assertIn(texto, html)

    def test_distribucion_no_fija_cantidad_de_filas_ni_columnas(self):
        html = self.renderizar(filas=[{
            "nombre": "VIP",
            "butacas": [
                {"id": "vip-1", "numero": 1, "ocupada": False},
                {"id": "vip-2", "numero": 2, "ocupada": False},
            ],
        }])
        butacas = [i for i in Formulario(html).inputs if i.get("name") == "butacas"]
        self.assertEqual([i["value"] for i in butacas], ["vip-1", "vip-2"])
        self.assertIn("Fila VIP, butaca 2", html)

    def test_ocupadas_no_se_marcan_y_no_hay_preseleccion_implicita(self):
        formulario = Formulario(self.renderizar(seleccionadas=["A3", "D5", "inexistente"]))
        self.assertEqual(
            [i["value"] for i in formulario.inputs if "checked" in i], ["D5"]
        )
        self.assertFalse(any("checked" in i for i in Formulario(self.renderizar()).inputs))

    def test_formulario_post_recibe_lista_y_token(self):
        formulario = Formulario(self.renderizar(seleccionadas=["D5", "D6"]))
        self.assertEqual(len(formulario.formularios), 1)
        form = formulario.formularios[0]
        self.assertEqual(form["method"].upper(), "POST")
        self.assertEqual(form["action"], "/funciones/42/butacas")
        datos = MultiDict(
            (i["name"], i["value"])
            for i in formulario.inputs
            if "disabled" not in i and (i["type"] == "hidden" or "checked" in i)
        )
        recibidos = {}

        def recibir(funcion_id):
            recibidos.update(
                funcion_id=funcion_id,
                butacas=request.form.getlist("butacas"),
                token=request.form["csrf_token"],
            )
            return "Solicitud recibida por la ruta de prueba"

        self.app.view_functions["cliente.elegir_butacas"] = recibir
        with self.app.test_client() as client:
            respuesta = client.post(form["action"], data=datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(recibidos, {
            "funcion_id": 42,
            "butacas": ["D5", "D6"],
            "token": "token-exclusivo-de-prueba",
        })
        self.assertEqual(set(datos.keys()), {"butacas", "csrf_token"})
        self.assertFalse(any("required" in i for i in formulario.inputs))

    def test_plano_vacio_y_error_de_carga_no_ofrecen_formulario(self):
        for contexto, mensaje in (
            ({"filas": []}, "No hay un plano de butacas disponible"),
            ({"filas": [{"nombre": "A", "butacas": []}]}, "No hay un plano"),
            ({"error_mapa": "No se pudo consultar la API."}, "No pudimos cargar"),
        ):
            with self.subTest(contexto=contexto):
                html = self.renderizar(**contexto)
                self.assertIn(mensaje, html)
                self.assertFalse(Formulario(html).formularios)

    def test_sala_completa_deshabilita_continuar(self):
        filas = self.filas()
        for fila in filas:
            for butaca in fila["butacas"]:
                butaca["ocupada"] = True
        html = self.renderizar(filas=filas)
        self.assertIn("No quedan butacas libres", html)
        formulario = Formulario(html)
        self.assertIn("disabled", formulario.botones[0])

    def test_error_de_seleccion_preserva_solo_las_butacas_libres(self):
        html = self.renderizar(
            seleccionadas=["A3", "D5"],
            error_seleccion="Una butaca ya no esta disponible.",
        )
        self.assertIn('role="alert"', html)
        self.assertIn("Una butaca ya no esta disponible.", html)
        self.assertIn('aria-describedby="asientos-ayuda asientos-error"', html)
        self.assertEqual(
            [i["value"] for i in Formulario(html).inputs if "checked" in i], ["D5"]
        )

    def test_escapa_datos_del_servidor(self):
        texto = '<script>alert("prueba")</script>'
        html = self.renderizar(
            funcion=self.funcion(pelicula={"titulo": texto}),
            error_seleccion=texto,
        )
        self.assertNotIn(texto, html)
        self.assertIn("&lt;script&gt;", html)

    def test_plantilla_anterior_reutiliza_el_mapa(self):
        self.assertEqual(
            self.renderizar(),
            self.renderizar(plantilla="cliente/elegir-butacas.html"),
        )


if __name__ == "__main__":
    unittest.main()
