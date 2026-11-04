from flask import Blueprint, render_template

cliente_views_bp = Blueprint("cliente_views", __name__)

@cliente_views_bp.route("/")
def inicio():
    return render_template("cliente/inicio.html")

@cliente_views_bp.route("/cartelera")
def cartelera():
    return render_template("cliente/cartelera.html")

@cliente_views_bp.route("/pelicula/", defaults={"id": 1})
@cliente_views_bp.route("/pelicula/<int:id>")
def detalle_pelicula(id):
    return render_template("cliente/detalle-pelicula.html")

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