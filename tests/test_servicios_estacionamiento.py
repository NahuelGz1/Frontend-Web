import re
import unittest
from unittest.mock import patch

from cachelib.simple import SimpleCache
from flask import session
from werkzeug.datastructures import MultiDict

from app import create_app
from services import compra_service


CATALOGO = [
    {"id": 1, "nombre": "Estacionamiento", "precio": 3000},
    {"id": 2, "nombre": "Estacionamiento cubierto", "precio": 4000},
    {"id": 3, "nombre": "Acceso VIP", "precio": 5000},
    {"id": 4, "nombre": "Agua", "precio": 1000},
]


def crear_app():
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test-key-" * 5,
        "SESSION_CACHELIB": SimpleCache(),
    })


def api_falsa(disponibles=2, error_compra=None, error_disponibilidad=None):
    def consumir(metodo, endpoint, **kwargs):
        if endpoint == "/servicios":
            return 200, {"ok": True, "data": [dict(s) for s in CATALOGO]}
        if endpoint == "/funciones/42/estacionamiento":
            if error_disponibilidad:
                return error_disponibilidad
            return 200, {"ok": True, "data": {"limite": 20, "vendidos": 20 - disponibles,
                                             "disponibles": disponibles}}
        if endpoint == "/funciones/42":
            return 200, {"ok": True, "data": {
                "fecha_hora_proyeccion": "2099-01-01 20:00:00",
                "precio_entrada": 10000,
                "pelicula": {"id": 7, "titulo": "Película"},
                "sala": {"nombre": "Sala 1", "local": "Centro"},
            }}
        if endpoint == "/peliculas/7":
            return 200, {"ok": True, "data": {}}
        if endpoint == "/compras" and metodo == "POST":
            if error_compra:
                return error_compra
            raise AssertionError("La compra no debería confirmarse")
        raise AssertionError((metodo, endpoint))
    return consumir


def preparar_cliente(app, servicios=None):
    client = app.test_client()
    with client.session_transaction() as sesion:
        sesion["access_token"] = "token"
        sesion["csrf_token"] = "csrf"
        sesion["usuario"] = {"nombre": "Cliente", "email": "cliente@example.com"}
        sesion["compra"] = {"id_funcion": 42, "butacas": [1, 2, 3],
                            "servicios": servicios or []}
    return client


def mocks_api(api):
    return patch.multiple("services.compra_service", consumir_api=api)


def test_tarjeta_y_limites():
    app = crear_app()
    for disponibles, limite in ((0, 0), (1, 1), (20, 3)):
        api = api_falsa(disponibles)
        with mocks_api(api), patch("routes.cliente_views.consumir_api", api):
            html = preparar_cliente(app).get("/servicios").get_data(as_text=True)
        tarjeta = re.search(r'<article[^>]*data-service-id="1".*?</article>', html, re.S).group()
        assert f'data-max-quantity="{limite}"' in tarjeta
        boton = re.search(r"<button[^>]*data-add[^>]*>", tarjeta).group()
        if disponibles == 0:
            assert "disabled" in boton
            assert "Estacionamiento agotado para esta función" in tarjeta
        else:
            assert "disabled" not in boton
            assert f"Máx. {limite} (Quedan {disponibles} lugares)" in tarjeta
        vip = re.search(r'<article[^>]*data-service-id="3".*?</article>', html, re.S).group()
        assert 'data-max-quantity="3"' in vip


def test_falla_consulta_sin_simular_agotado():
    app = crear_app()
    for error in ((503, {"error": {"message": "Error"}}),
                  (200, {"data": {"disponibles": 21}}),
                  (200, {"data": {"disponibles": True}})):
        api = api_falsa(error_disponibilidad=error)
        with mocks_api(api), patch("routes.cliente_views.consumir_api", api):
            html = preparar_cliente(app).get("/servicios").get_data(as_text=True)
        tarjeta = re.search(r'<article[^>]*data-service-id="1".*?</article>', html, re.S).group()
        assert "No pudimos consultar la disponibilidad" in tarjeta
        assert "agotado" not in tarjeta
        assert "disabled" in re.search(r"<button[^>]*data-add[^>]*>", tarjeta).group()


def test_validar_cantidades_y_agregado():
    app = crear_app()
    with app.test_request_context(), mocks_api(api_falsa(2)):
        session["compra"] = {"id_funcion": 42, "butacas": [1, 2, 3], "servicios": []}
        assert compra_service.guardar_servicios(MultiDict({"cantidad_1": "2"})) is None
        assert "Quedan 2" in compra_service.guardar_servicios(MultiDict({"cantidad_1": "3"}))
        assert "por entrada" in compra_service.guardar_servicios(MultiDict({"cantidad_1": "4"}))
        assert "por entrada" in compra_service.guardar_servicios(
            MultiDict({"cantidad_1": "2", "cantidad_2": "2"}))
        assert "Quedan 2" in compra_service.guardar_servicios(
            MultiDict({"cantidad_1": "2", "cantidad_2": "1"}))
        assert "repetidos" in compra_service.guardar_servicios(
            MultiDict({"cantidad_1": "1", "cantidad_01": "1"}))
        assert "por entrada" in compra_service.guardar_servicios(MultiDict({"cantidad_3": "4"}))
        assert compra_service.guardar_servicios(MultiDict({"cantidad_4": "10"})) is None
    with app.test_request_context(), mocks_api(api_falsa(0)):
        session["compra"] = {"id_funcion": 42, "butacas": [1], "servicios": []}
        assert "Quedan 0" in compra_service.guardar_servicios(MultiDict({"cantidad_1": "1"}))


def test_resumen_ajusta_con_aviso_y_limite_global():
    app = crear_app()
    with app.test_request_context(), mocks_api(api_falsa(2)):
        session["compra"] = {"id_funcion": 42, "butacas": [1, 2, 3], "servicios": [
            {"id_servicio": 1, "cantidad": 2}, {"id_servicio": 2, "cantidad": 2}]}
        resumen, error = compra_service.armar_resumen()
        assert error is None
        assert resumen["servicios"][0]["cantidad"] == 2
        assert len(resumen["servicios"]) == 1
        assert "disponibilidad de estacionamiento cambió" in resumen["aviso"]
        assert session["compra"]["servicios"] == [{"id_servicio": 1, "cantidad": 2}]
    with app.test_request_context(), mocks_api(api_falsa(0)):
        session["compra"] = {"id_funcion": 42, "butacas": [1], "servicios": [
            {"id_servicio": 1, "cantidad": 1}]}
        resumen, error = compra_service.armar_resumen()
        assert error is None and not resumen["servicios"] and resumen["aviso"]


def test_cambio_al_confirmar_obliga_a_revisar():
    app = crear_app()
    client = preparar_cliente(app, [{"id_servicio": 1, "cantidad": 3}])
    api = api_falsa(1)
    with mocks_api(api):
        respuesta = client.post("/pagar", data={"csrf_token": "csrf", "email": "cliente@example.com"})
        assert respuesta.status_code == 302 and respuesta.location.endswith("/pagar")
        respuesta = client.get("/pagar")
        assert "disponibilidad de estacionamiento cambió" in respuesta.get_data(as_text=True)
    with client.session_transaction() as sesion:
        assert sesion["compra"]["servicios"] == [{"id_servicio": 1, "cantidad": 1}]


def test_rechazo_400_y_preservacion_compra():
    app = crear_app()
    client = preparar_cliente(app, [{"id_servicio": 1, "cantidad": 1}])
    error = (400, {"ok": False, "error": {"message":
             "No hay suficientes espacios de estacionamiento disponibles para esta función. Quedan 0 lugares."}})
    api = api_falsa(1, error_compra=error)
    with mocks_api(api), patch("routes.cliente_views.consumir_api", api):
        respuesta = client.post("/pagar", data={"csrf_token": "csrf", "email": "cliente@example.com"})
        assert respuesta.status_code == 302 and respuesta.location.endswith("/servicios")
        assert "Quedan 0 lugares" in client.get("/servicios").get_data(as_text=True)
    with client.session_transaction() as sesion:
        assert sesion["compra"]["butacas"] == [1, 2, 3]
        assert "compra_confirmada" not in sesion


def test_error_disponibilidad_y_compra_sin_estacionamiento():
    app = crear_app()
    error = (503, {"ok": False, "error": {"message": "Error"}})
    with app.test_request_context(), mocks_api(api_falsa(error_disponibilidad=error)):
        session["compra"] = {"id_funcion": 42, "butacas": [1], "servicios": [
            {"id_servicio": 1, "cantidad": 1}]}
        resumen, mensaje = compra_service.armar_resumen()
        assert resumen is None and "disponibilidad de estacionamiento" in mensaje
        assert session["compra"]["servicios"] == [{"id_servicio": 1, "cantidad": 1}]
        assert "disponibilidad de estacionamiento" in compra_service.guardar_servicios(
            MultiDict({"cantidad_1": "1"}))
        assert compra_service.guardar_servicios(MultiDict({"cantidad_4": "2"})) is None
        resumen, mensaje = compra_service.armar_resumen()
        assert mensaje is None and resumen["servicios"][0]["cantidad"] == 2


def test_rechazo_no_relacionado_y_compra_exitosa():
    app = crear_app()
    client = preparar_cliente(app)
    api = api_falsa(error_compra=(400, {"ok": False, "error": {"message": "Butaca ya vendida"}}))
    with mocks_api(api):
        respuesta = client.post("/pagar", data={"csrf_token": "csrf", "email": "cliente@example.com"})
        assert respuesta.location.endswith("/elegir-butacas/42")
    with app.test_request_context():
        session["usuario"] = {"email": "cliente@example.com"}
        session["compra"] = {"id_funcion": 42, "butacas": [1], "servicios": []}
        resumen = {"id_funcion": 42, "butacas": [1], "servicios": [], "vista": {
            "funcion": {}, "subtotal_entradas": "$10", "servicios_seleccionados": [],
            "subtotal_servicios": "$0", "total_compra": "10"}}
        with patch("services.compra_service.consumir_api", return_value=(
                201, {"ok": True, "data": {"id_compra": 9, "entradas": []}})):
            exito, mensaje, destino = compra_service.confirmar_compra(resumen)
        assert exito and mensaje is None and not destino
        assert "compra" not in session and compra_service.id_compra_confirmada() == 9


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    for funcion in (test_tarjeta_y_limites, test_falla_consulta_sin_simular_agotado,
                    test_validar_cantidades_y_agregado, test_resumen_ajusta_con_aviso_y_limite_global,
                    test_cambio_al_confirmar_obliga_a_revisar, test_rechazo_400_y_preservacion_compra,
                    test_error_disponibilidad_y_compra_sin_estacionamiento,
                    test_rechazo_no_relacionado_y_compra_exitosa):
        suite.addTest(unittest.FunctionTestCase(funcion))
    return suite
