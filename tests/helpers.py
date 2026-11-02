import unittest
from html.parser import HTMLParser
from pathlib import Path

from flask import Flask
from jinja2 import StrictUndefined


ROOT = Path(__file__).resolve().parents[1]


class Formulario(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.formularios = []
        self.inputs = []
        self.labels = []
        self.botones = []
        self.selects = []
        self.select_actual = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag == "form":
            self.formularios.append(atributos)
        elif tag == "input":
            self.inputs.append(atributos)
        elif tag == "label":
            self.labels.append(atributos)
        elif tag == "button":
            self.botones.append(atributos)
        elif tag == "select":
            self.select_actual = {**atributos, "opciones": []}
            self.selects.append(self.select_actual)
        elif tag == "option" and self.select_actual is not None:
            self.select_actual["opciones"].append(atributos)

    def handle_endtag(self, tag):
        if tag == "select":
            self.select_actual = None


class PruebaPlantillas(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__,
            template_folder=str(ROOT / "templates"),
            static_folder=str(ROOT / "static"),
        )
        self.app.config["TESTING"] = True
        self.app.jinja_env.undefined = StrictUndefined
        # Rutas de prueba: los Blueprints publicos aun no estan implementados.
        for endpoint, ruta in (
            ("cliente.cartelera", "/cartelera"),
            ("cliente.servicios", "/servicios"),
            ("cliente.mi_perfil", "/mi-perfil"),
            ("cliente.elegir_butacas", "/funciones/<int:funcion_id>/butacas"),
            ("cliente.checkout", "/funciones/<int:funcion_id>/checkout"),
            ("cliente.cancelar_reserva", "/reservas/<reserva_id>/cancelar"),
            ("auth.iniciar_sesion", "/iniciar-sesion"),
        ):
            metodos = (
                ["GET", "POST"]
                if endpoint in ("cliente.elegir_butacas", "cliente.checkout")
                else ["GET"]
            )
            if endpoint == "cliente.cancelar_reserva":
                metodos = ["POST"]
            self.app.add_url_rule(ruta, endpoint=endpoint, methods=metodos)

    def funcion(self, identificador=42, **cambios):
        datos = {
            "id": identificador,
            "pelicula": {"titulo": "Volver al Futuro"},
            "fecha": "2026-10-30",
            "horario": "19:30",
            "sala": {"nombre": "Sala 1"},
            "disponible": True,
        }
        datos.update(cambios)
        return datos
