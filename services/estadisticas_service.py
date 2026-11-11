from types import SimpleNamespace
from services.api_client import consumir_api

def obtener_estadisticas_dashboard(token, complejo=None):
    if not token:
        return 401, None

    status_code, respuesta = consumir_api(
        metodo="GET",
        endpoint="/dashboard/ocupacion",
        headers={"Authorization": "Bearer " + token},
        params={"complejo": complejo} if complejo else None,
    )

    if status_code != 200:
        return status_code, None

    data = respuesta.get("data", {}) if isinstance(respuesta, dict) else {}

    # --- Procesamiento y cálculos ---
    resumen_raw = data.get("resumen_general", {})
    vendidas = int(resumen_raw.get("total_vendidas", 0))
    canceladas = int(resumen_raw.get("total_canceladas", 0))
    emitidas = int(resumen_raw.get("total_generadas", 0))
    ingresos_totales = float(resumen_raw.get("total_ingresos", 0))
    cap_total = sum(int(p.get("capacidad_total_ofertada", 0)) for p in data.get("por_pelicula", []))

    resumen = {
        "entradas_netas": vendidas,
        "entradas_emitidas": emitidas,
        "entradas_canceladas": canceladas,
        "capacidad_total": cap_total,
        "ocupacion_porcentaje": round((vendidas / cap_total * 100), 1) if cap_total > 0 else 0,
        "ingresos_entradas": f"$ {ingresos_totales:,.0f}".replace(",", ".") if ingresos_totales > 0 else "$ 0",
        "tasa_cancelacion": round((canceladas / emitidas * 100), 1) if emitidas > 0 else 0,
    }

    ocupacion_funciones = [
        {
            "pelicula_titulo": f.get("pelicula_titulo", ""),
            "fecha_hora": str(f.get("fecha_hora_proyeccion", "")),
            "complejo_nombre": f.get("cine_local", "Cine"),
            "sala_nombre": f.get("sala_nombre", ""),
            "entradas_netas": int(f.get("butacas_ocupadas", 0)),
            "capacidad": int(f.get("sala_capacidad", 0)),
            "ocupacion_porcentaje": round((int(f.get("butacas_ocupadas", 0)) / (int(f.get("sala_capacidad", 1)) or 1) * 100), 1),
            "entradas_emitidas": int(f.get("butacas_ocupadas", 0)) + int(f.get("butacas_canceladas", 0)),
            "entradas_canceladas": int(f.get("butacas_canceladas", 0)),
            "ingresos_formateados": f"$ {float(f.get('total_ingresos', 0)):,.0f}".replace(",", ".") if f.get("total_ingresos") else "$ 0"
        } for f in data.get("por_funcion", [])
    ]

    ocupacion_peliculas = [
        {
            "titulo": p.get("pelicula_titulo", ""),
            "cantidad_funciones": int(p.get("total_funciones", 0)),
            "entradas_netas": int(p.get("total_entradas_vendidas", 0)),
            "capacidad": int(p.get("capacidad_total_ofertada", 0)),
            "ocupacion_porcentaje": round((int(p.get("total_entradas_vendidas", 0)) / (int(p.get("capacidad_total_ofertada", 1)) or 1) * 100), 1),
            "ingresos_formateados": f"$ {float(p.get('total_ingresos', 0)):,.0f}".replace(",", ".") if p.get("total_ingresos") else "$ 0"
        } for p in data.get("por_pelicula", [])
    ]

    ventas_genero = [
        {
            "nombre": g.get("genero", "Sin Género"),
            "entradas_netas": int(g.get("total_entradas", 0)),
            "porcentaje": round((int(g.get("total_entradas", 0)) / vendidas * 100), 1) if vendidas > 0 else 0,
            "ingresos_formateados": f"$ {float(g.get('total_ingresos', 0)):,.0f}".replace(",", ".") if g.get("total_ingresos") else "$ 0"
        } for g in data.get("por_genero", [])
    ]

    raw_franjas = [
        {
            "nombre": f"{int(h.get('hora', 0)):02d}:00 hs",
            "entradas_netas": int(h.get("total_entradas", 0)),
            "cantidad_funciones": 1,
            "porcentaje": round((int(h.get("total_entradas", 0)) / vendidas * 100), 1) if vendidas > 0 else 0,
            "ingresos_formateados": f"$ {float(h.get('total_ingresos', 0)):,.0f}".replace(",", ".") if h.get("total_ingresos") else "$ 0"
        } for h in data.get("por_franja_horaria", [])
    ]
    ventas_franjas = [SimpleNamespace(**item) for item in raw_franjas]

    datos_procesados = {
        "resumen": resumen,
        "ocupacion_funciones": ocupacion_funciones,
        "ocupacion_peliculas": ocupacion_peliculas,
        "ventas_genero": ventas_genero,
        "ventas_franjas": ventas_franjas,
        "cancelaciones": []
    }

    return 200, datos_procesados