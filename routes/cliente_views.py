from flask import Blueprint, render_template, redirect, url_for, flash
from services.api_client import consumir_api


cliente_views_bp = Blueprint("cliente_views", __name__)

@cliente_views_bp.route("/")
def inicio():
    status_code, respuesta = consumir_api("GET", "/peliculas/cartelera")
    
    peliculas = []
    if status_code == 200:
        peliculas = respuesta.get("data") or []

    # Normalizamos los nombres de campos que espera inicio.html
    for peli in peliculas:
        if not peli.get("afiche_url"):
            peli["afiche_url"] = peli.get("poster")
        if not peli.get("duracion_minutos"):
            peli["duracion_minutos"] = peli.get("duracion")

    # La primera pelicula como destacada, las demas para la grilla de hoy
    pelicula_destacada = peliculas[0] if peliculas else None
    peliculas_hoy = peliculas[1:] if len(peliculas) > 1 else peliculas
    return render_template(
        "cliente/inicio.html",
        pelicula_destacada=pelicula_destacada,
        peliculas_hoy=peliculas_hoy,
        proximos_estrenos=[]
)



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
    status_code, respuesta = consumir_api("GET", "/servicios")
    
    lista_servicios = []
    if status_code == 200:
        lista_servicios = respuesta.get("data") or []

    for servicio in lista_servicios:
        nombre = servicio.get("nombre", "").lower()
        
        if not servicio.get("categoria"):
            if "pochoclo" in nombre or "combo" in nombre:
                servicio["categoria"] = "pochoclos"

            elif "agua" in nombre or "gaseosa" in nombre or "bebida" in nombre:
                servicio["categoria"] = "bebidas"

            elif "estacionamiento" in nombre or "vip" in nombre:
                servicio["categoria"] = "mejoras de experiencia"
                
            else:
                servicio["categoria"] = "snacks"

        if not servicio.get("precio_formateado") and "precio" in servicio:
            servicio["precio_formateado"] = f"${int(servicio['precio']):,}".replace(",", ".")

    return render_template("cliente/servicios.html", servicios=lista_servicios)


@cliente_views_bp.route("/mi-perfil")
def mi_perfil():
    status_code, respuesta = consumir_api("GET", "/auth/usuarios/me/perfil-completo")
    datos_perfil = respuesta.get("data", {}) if status_code == 200 else {}
    return render_template("cliente/mi-perfil.html", **datos_perfil)


@cliente_views_bp.route("/pagar")
def pagar():
    return render_template("cliente/pagar.html")

@cliente_views_bp.route("/compra-exitosa")
def compra_exitosa():
    return render_template("cliente/compra-exitosa.html")

@cliente_views_bp.route("/cancelar-compra")
def cancelar_compra():
    return render_template("cliente/cancelar-compra.html")
