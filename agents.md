# Directrices para agentes y desarrolladores — Cine Paradiso Frontend

Este documento es obligatorio para cualquier agente de inteligencia artificial (Copilot,
Cursor, Claude u otro) y para cualquier persona que contribuya al repositorio Frontend de
Cine Paradiso. Si una solicitud contradice estas reglas, debe señalarse el conflicto antes
de modificar el código.

## 1. Rol y objetivo del agente

El agente actúa como un desarrollador senior de Flask responsable de entregar cambios
pequeños, trazables, seguros y mantenibles. Debe:

- comprender primero la estructura existente y reutilizar sus patrones;
- implementar la funcionalidad completa en las capas correspondientes, sin atajos;
- mantener separadas las vistas, la lógica de integración y las plantillas;
- validar los cambios con las herramientas disponibles antes de darlos por terminados;
- informar explícitamente errores, supuestos, limitaciones y validaciones realizadas;
- no modificar archivos ajenos a la tarea ni introducir dependencias innecesarias.

El frontend es una aplicación web Python con Flask, Jinja2 y HTML/CSS responsive. Consume
únicamente la API REST interna y, desde el servidor, catálogos externos de películas como
OMDb API o TMDb. No es una SPA: el navegador solicita páginas al servidor y recibe HTML
renderizado.

## 2. Alcance funcional

### Front público — clientes

Debe contemplar cartelera (sinopsis, póster, duración y clasificación), selección de
función y butacas libres/ocupadas, checkout de entradas, servicios adicionales (comida,
bebidas, estacionamiento y VIP), confirmación con código QR, cancelación dentro del plazo
permitido, perfil e historial de consumos.

### Backoffice — administradores

Debe contemplar carga y edición de películas, configuración de salas, funciones y
servicios, dashboards de ventas por género, ocupación, franjas horarias y cancelaciones,
y validación o escaneo de QR para el ingreso.

La fuente de verdad de reservas, usuarios, pagos, disponibilidad y permisos es la API
REST interna. Este repositorio no accede directamente a su base de datos.

## 3. Estructura de directorios obligatoria o recomendada
> **Nota de estado:** La estructura actual del repositorio contiene las carpetas `templates/` y `static/`. El paquete Python `app/` (Blueprints, clientes API con `requests` y utilidades) representa la arquitectura modular objetivo a implementar en las siguientes tareas.

La estructura propuesta es:

```text
.
├── app/
│   ├── __init__.py              # Fábrica create_app y registro de Blueprints
│   ├── config.py                # Configuración desde variables de entorno
│   ├── clientes_api/
│   │   ├── __init__.py
│   │   ├── interno.py           # Cliente de la API REST del sistema
│   │   └── catalogo.py          # OMDb/TMDb mediante requests
│   ├── cliente/
│   │   ├── __init__.py           # Blueprint del front público
│   │   ├── rutas.py
│   │   └── forms.py
│   ├── admin/
│   │   ├── __init__.py           # Blueprint del backoffice
│   │   ├── rutas.py
│   │   └── forms.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── rutas.py
│   ├── errores.py
│   └── utils/
│       ├── auth.py               # Decoradores y validaciones de rol
│       └── validacion.py
├── templates/
│   ├── layouts/base.html
│   ├── auth/
│   ├── cliente/
│   ├── admin/
│   └── emails/
├── static/
│   ├── css/
│   ├── images/
│   └── js/                       # Solo comportamiento visual/local
├── tests/
├── init.sh                       # Instalación reproducible de dependencias
├── .env.example
└── README.md
```

Los nombres pueden adaptarse a la estructura ya existente, pero la separación de
responsabilidades no debe eliminarse. Las rutas coordinan la petición y la respuesta;
los clientes API realizan comunicaciones; los formularios validan entradas; las
plantillas presentan datos.

Cada módulo funcional debe exponerse mediante un `Blueprint`. La aplicación debe usar una
fábrica `create_app()` para poder configurar y probar el sistema sin depender de estado
global.

## 4. Restricciones técnicas inquebrantables

### 4.1 Prohibición total de llamadas asíncronas desde el cliente

Está prohibido generar desde el navegador peticiones al backend o a APIs externas usando
JavaScript. No se permite `fetch`, `axios`, `XMLHttpRequest`, `Promise`, `async/await`,
WebSocket, SSE ni equivalentes para obtener o enviar datos.

El JavaScript permitido se limita a comportamiento local de interfaz: abrir/cerrar un
menú, validar una interacción visual o actualizar estilos con datos ya renderizados.
Nunca debe contener URLs de APIs, tokens, credenciales ni lógica de reservas o pagos.

**Prohibido:**

```javascript
// Nunca hacer llamadas de red desde static/js/.
fetch("/api/funciones?pelicula=42")
  .then((respuesta) => respuesta.json())
  .then((funciones) => mostrarFunciones(funciones));
```

### 4.2 Comunicación exclusivamente server-side

Toda comunicación con la API interna o con OMDb/TMDb se ejecuta en Python, desde Flask,
mediante `requests`. Las claves se leen desde variables de entorno y nunca se escriben
en el repositorio, las plantillas o el navegador.

**Permitido:**

```python
# app/clientes_api/interno.py
import requests


class ErrorApiInterna(Exception):
    """Indica que la API interna no pudo atender la operación."""


def crear_reserva(base_url, token, datos):
    respuesta = requests.post(
        f"{base_url}/reservas",
        json=datos,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if not respuesta.ok:
        raise ErrorApiInterna(
            f"La API rechazó la reserva con estado {respuesta.status_code}"
        )
    return respuesta.json()
```

La ruta usa el cliente, maneja el error según el estándar de la aplicación y renderiza la
plantilla:

```python
# app/cliente/rutas.py
from flask import Blueprint, current_app, flash, redirect, render_template, url_for

from app.clientes_api.interno import ErrorApiInterna, crear_reserva

bp = Blueprint("cliente", __name__, url_prefix="/cliente")


@bp.post("/reservas")
def reservar():
    datos = obtener_datos_validados_del_formulario()
    try:
        reserva = crear_reserva(
            current_app.config["API_INTERNA_URL"],
            obtener_token_de_sesion(),
            datos,
        )
    except ErrorApiInterna:
        current_app.logger.exception("No se pudo crear la reserva")
        flash("No fue posible completar la reserva. Intenta nuevamente.", "error")
        return redirect(url_for("cliente.checkout"))

    return render_template("cliente/compra-exitosa.html", reserva=reserva)
```

El ejemplo es ilustrativo: debe utilizarse el formulario, helper de sesión y manejo de
errores que existan en el proyecto. Nunca se deben ocultar excepciones con `except:
pass`, valores ficticios ni respuestas exitosas falsas.

### 4.3 Sin ORM ni SQL

Este repositorio no contiene modelos ORM, migraciones, consultas SQL ni conexiones
directas a bases de datos. Todos los datos se obtienen y modifican mediante la API REST
interna en JSON. No se deben agregar SQLite, SQLAlchemy, psycopg, consultas SQL ni
repositorios de persistencia local.

### 4.4 Modularidad y calidad

- No usar variables globales mutables para sesiones, usuarios, reservas, configuración o
  resultados de API.
- No crear ciclos infinitos, polling del navegador ni procesos residentes.
- No duplicar validaciones, llamadas HTTP o lógica de autorización: extraer helpers o
  servicios claros.
- Toda llamada HTTP debe tener `timeout`, validar el estado de respuesta y tratar errores
  de red, respuestas inválidas y estados no autorizados.
- Validar en servidor toda entrada del usuario. La validación HTML/JavaScript no sustituye
  la validación backend.
- No registrar tokens, contraseñas, datos de pago ni información personal sensible.
- Mantener HTML semántico y CSS responsive para móviles, tablets y escritorio. No agregar
  librerías pesadas o frameworks no autorizados por la cátedra.

## 5. Formularios, plantillas y experiencia de usuario

Los formularios deben usar métodos HTTP apropiados, nombres consistentes y mensajes
claros. Los datos deben validarse antes de llamar a la API. Las plantillas deben heredar
de `layouts/base.html`, escapar datos dinámicos con Jinja2 y mostrar estados de carga,
éxito y error sin inventar información.

Las butacas deben mostrar claramente libres y ocupadas, pero la disponibilidad definitiva
la confirma la API al crear la reserva. El frontend no debe asumir que una butaca sigue
libre entre la selección y el checkout.

Los códigos QR deben mostrarse únicamente con la respuesta confirmada por el backend. La
cancelación debe respetar el límite de tiempo calculado por la API; el cliente no puede
forzar una cancelación vencida manipulando el HTML o JavaScript.

## 6. Sesiones, autenticación y roles

La sesión Flask debe almacenar solo identificadores y datos mínimos necesarios, nunca
contraseñas, tokens de pago, códigos QR completos ni información sensible. Las claves de
sesión y secretos deben provenir del entorno y no de valores hardcodeados.

Los roles válidos son:

- **Cliente:** cartelera, detalle de película, selección de función y butacas, checkout,
  servicios, confirmación, cancelación válida, perfil e historial propio.
- **Administrador:** operaciones del backoffice, configuración, reportes y validación de
  QR, siempre autorizadas por la API.

Toda ruta protegida debe verificar autenticación y rol en el servidor, preferentemente
mediante decoradores o helpers reutilizables. Ocultar un enlace en una plantilla no es
control de acceso. Un cliente nunca puede consultar o modificar recursos de otro cliente
cambiando un identificador en la URL.

Las respuestas `401` y `403` deben dirigir a una pantalla o mensaje coherente, sin
reintentos infinitos. Después de iniciar o cerrar sesión, regenerar o limpiar el estado
de sesión según corresponda.

## 7. Catálogo externo de películas

La integración con OMDb o TMDb debe estar encapsulada en
`app/clientes_api/catalogo.py`. Debe:

- leer URL, clave y parámetros desde configuración;
- usar `requests` exclusivamente en el servidor y establecer `timeout`;
- validar la respuesta y mapearla a un formato interno estable;
- manejar límites, errores de red, respuestas incompletas y películas no encontradas;
- evitar exponer la clave al cliente o persistir respuestas en una base local;
- evitar llamadas innecesarias y no bloquear una pantalla con reintentos infinitos.

La API interna debe seguir siendo la fuente de verdad para datos operativos del cine,
reservas y disponibilidad.

## 8. Dependencias e inicialización

Las dependencias deben instalarse **exclusivamente** mediante el script ejecutable
`init.sh`. No instalar paquetes manualmente ni introducir instrucciones alternativas que
generen entornos incompatibles.

El script debe ser reproducible, fallar ante errores y utilizar el gestor de paquetes
definido por el proyecto. Si se agrega o elimina una dependencia, actualizar `init.sh` y
la documentación relacionada en el mismo cambio. Nunca incluir secretos, archivos `.env`
reales o credenciales.

## 9. Guía de trabajo: qué hacer

Antes de editar:

1. leer `README.md`, `agents.md`, `.env.example` y los módulos relacionados;
2. identificar la tarjeta de GitHub Projects/backlog asociada;
3. buscar helpers o patrones existentes antes de crear otros;
4. definir la ruta, cliente API, formulario, plantilla y validaciones necesarias;
5. revisar si el cambio afecta simultáneamente al front público y al backoffice.

Durante la implementación:

- mantener el flujo request → Blueprint → cliente API → plantilla;
- usar nombres en español coherentes con el dominio existente;
- devolver HTML renderizado desde Flask, no JSON para ser procesado por JavaScript del
  navegador;
- tratar explícitamente errores de autenticación, validación, red y API;
- mantener cambios acotados y actualizar pruebas o documentación directamente relacionada.

Antes de entregar:

- ejecutar las pruebas, linting o validaciones disponibles;
- comprobar que no se introdujeron llamadas asíncronas ni secretos;
- verificar que las rutas protegidas requieren el rol correcto;
- revisar el diff completo y confirmar que solo contiene cambios de la tarea;
- informar qué se validó y qué no pudo validarse.

## 10. Qué NUNCA hacer

- Nunca usar `fetch`, `axios`, `XMLHttpRequest`, `Promise`, `async/await` o equivalentes
  para comunicarse con el backend o servicios externos desde el navegador.
- Nunca llamar OMDb, TMDb o la API interna directamente desde `static/js/`.
- Nunca agregar ORM, SQL, migraciones o acceso directo a la base de datos.
- Nunca poner claves API, contraseñas, tokens o datos sensibles en el código, HTML, logs,
  JavaScript, commits o archivos `.env` versionados.
- Nunca confiar en un rol, precio, disponibilidad, límite de cancelación o resultado
  calculado en el cliente.
- Nunca usar estado global mutable, ciclos infinitos, polling o reintentos sin límite.
- Nunca ignorar un error con `except: pass`, devolver éxito simulado o ocultar un fallo de
  la API.
- Nunca cambiar configuración de infraestructura, contratos de la API o dependencias sin
  documentar el impacto y asociarlo a una tarea.
- Nunca mezclar refactors no relacionados con la funcionalidad solicitada.

## 11. Git y GitHub Projects

Cada cambio debe estar asociado explícitamente a una tarjeta del tablero Kanban/backlog.
Antes de comenzar, usar el identificador de la tarjeta o del issue correspondiente. Si no
existe una tarjeta, crearla o solicitar que se cree antes de implementar una funcionalidad
no trivial.

Los commits deben:

- ser pequeños y atómicos;
- describir la tarea y el resultado en modo imperativo;
- incluir el identificador de la tarjeta o issue;
- no mezclar formato, dependencias y funcionalidades sin relación.

Formato recomendado:

```text
<tipo>(<área>): <acción concreta> [PROJ-123]
```

Ejemplos:

```text
feat(cliente): integrar selección server-side de butacas [PROJ-123]
fix(auth): restringir rutas de administración por rol [PROJ-145]
docs: documentar configuración del catálogo TMDb [PROJ-151]
```

En el Pull Request se debe enlazar la tarjeta, describir el comportamiento implementado,
indicar riesgos y enumerar las validaciones ejecutadas. El PR debe dejar claro qué
criterio de aceptación de la tarjeta se cumple. No marcar una tarjeta como terminada si
faltan pruebas, documentación, manejo de errores o integración con la API.

## 12. Criterio de aceptación técnico

Un cambio se considera terminado solo cuando:

1. respeta la comunicación exclusivamente server-side con `requests`;
2. no agrega ORM, SQL, llamadas asíncronas del cliente ni secretos;
3. usa Blueprints, sesiones y roles de forma consistente;
4. maneja correctamente éxito, validación, autorización y fallos de API;
5. conserva el diseño responsive y las plantillas Jinja2 existentes;
6. tiene la tarjeta de GitHub Projects/backlog y commits claramente asociados;
7. fue validado con las pruebas y herramientas disponibles, con resultados documentados.
