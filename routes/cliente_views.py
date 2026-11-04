from flask import Blueprint, render_template, redirect, url_for, flash
from services.api_client import consumir_api


cliente_views_bp = Blueprint("cliente_views", __name__)

@cliente_views_bp.route("/")
def inicio():
    status_code, respuesta = consumir_api("GET", "/peliculas/cartelera")
    
    peliculas = []
    if status_code == 200:
        peliculas = respuesta.get("data") or []
    for p in peliculas:
        if not p.get("afiche_url"):
            p["afiche_url"] = p.get("poster")
        if not p.get("duracion_minutos"):
            p["duracion_minutos"] = p.get("duracion")
    return render_template("cliente/inicio.html",peliculas_hoy=peliculas)



@cliente_views_bp.route("/cartelera")
def cartelera():
    status_code, respuesta = consumir_api("GET", "/peliculas/cartelera")

    peliculas = []
    if status_code == 200:
        peliculas = respuesta.get("data") or []

    for pelicula in peliculas:
        if not pelicula.get("poster_url"):
            pelicula["poster_url"] = pelicula.get("poster")

    return render_template("cliente/cartelera.html", peliculas=peliculas)



# Si entran a la ruta vacia sin ID (con o sin barra al final), los mandamos a la cartelera
@cliente_views_bp.route("/pelicula")
@cliente_views_bp.route("/pelicula/")
def detalle_pelicula_vacia():
    return redirect(url_for("cliente_views.cartelera"))

# Las rutas que esperan si o si un ID de película
@cliente_views_bp.route("/pelicula/<int:id>")
@cliente_views_bp.route("/pelicula/<int:pelicula_id>")
def detalle_pelicula(id=None, pelicula_id=None):
    pelicula_id = pelicula_id or id
    status_code, respuesta = consumir_api("GET", f"/peliculas/{pelicula_id}")

    # Si no se encuentra (404) o hubo error en el backend
    if status_code != 200:
        mensaje_error = respuesta.get("error", {}).get("message", "Película no encontrada.")
        flash(mensaje_error, "danger")
        return redirect(url_for("cliente_views.cartelera"))

    pelicula = respuesta.get("data") or {}

    if not pelicula.get("poster_url"):
        pelicula["poster_url"] = pelicula.get("poster")

    return render_template("cliente/detalle-pelicula.html", pelicula=pelicula)




@cliente_views_bp.route("/seleccion-funcion")
def seleccion_funcion():
    return render_template("cliente/seleccion_funcion.html")

@cliente_views_bp.route("/mapa-asientos")
def mapa_asientos():
    return render_template("cliente/mapa_asientos.html")

@cliente_views_bp.route("/elegir-butacas")
def elegir_butacas():
    return render_template("cliente/elegir-butacas.html")

@cliente_views_bp.route("/servicios")
def servicios():
    return render_template("cliente/servicios.html")

@cliente_views_bp.route("/pagar")
def pagar():
    return render_template("cliente/pagar.html")

@cliente_views_bp.route("/compra-exitosa")
def compra_exitosa():
    return render_template("cliente/compra-exitosa.html")

@cliente_views_bp.route("/cancelar-compra")
def cancelar_compra():
    return render_template("cliente/cancelar-compra.html")

@cliente_views_bp.route("/mi-perfil")
def mi_perfil():
    return render_template("cliente/mi-perfil.html")