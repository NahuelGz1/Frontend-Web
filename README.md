# Cine Paradiso — Frontend Web

Interfaz web de **Cine Paradiso**, desarrollada con **Python, Flask, plantillas HTML (Jinja2), CSS y JavaScript**. Permite a los clientes consultar la cartelera y las funciones, seleccionar butacas y servicios adicionales, realizar compras y consultar su perfil. Incluye vistas de administración para gestionar películas, salas, funciones y servicios, consultar métricas y validar códigos QR.

> Este repositorio contiene la **aplicación web (frontend)**. La API REST y el acceso a MySQL están en el repositorio [Backend_Api](https://github.com/NahuelGz1/Backend_Api). La comunicación con la API se realiza desde el servidor Flask mediante `requests`; el navegador no necesita conectarse directamente a MySQL.

## Tecnologías

- **Python 3 y Flask 3.1.2:** servidor web, rutas y plantillas.
- **Jinja2, HTML, CSS y JavaScript:** presentación e interacciones.
- **Requests:** peticiones HTTP a `Backend_Api`.
- **Flask-Session y Cachelib:** sesiones del lado del servidor.
- **python-dotenv:** carga de variables de entorno desde `.env`.
- **Gunicorn:** ejecución mediante WSGI en contenedores.

Las dependencias se enumeran en [`requirements.txt`](requirements.txt). El [`Dockerfile`](Dockerfile) utiliza Python 3.12.

## Requisitos previos

- Python 3 (se recomienda **3.12**, utilizado por el `Dockerfile`) y `venv`.
- Git.
- El proyecto **Backend_Api** instalado, configurado y ejecutándose, por defecto en `http://127.0.0.1:5000`.
- MySQL configurado **en el backend**: el frontend no se conecta directamente a la base de datos.

## Instalación local

### 1. Clonar el repositorio

```bash
git clone https://github.com/NahuelGz1/Frontend-Web.git
cd Frontend-Web
```

Si ya tenés el proyecto clonado, no hace falta volver a clonarlo.

### 2. Crear y activar el entorno virtual

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Instalá las dependencias en cualquiera de los dos sistemas:

```bash
python -m pip install -r requirements.txt
```

> El repositorio también dispone de `init.sh`, que prepara un entorno llamado `venv`, instala las dependencias y crea `.env` si no existe. Los pasos manuales anteriores usan `.venv` como alternativa. No hace falta crear ambos.

### 3. Configurar las variables de entorno

Creá el archivo `.env` a partir de [`.env.example`](.env.example).

**Linux / macOS:**

```bash
cp .env.example .env
```

**Windows (PowerShell):**

```powershell
Copy-Item .env.example .env
```

Verificá especialmente estos valores:

```dotenv
PORT=3000
API_BASE_URL=http://127.0.0.1:5000/api
SECRET_KEY=reemplazar_con_una_clave_aleatoria_de_al_menos_32_caracteres
SESSION_COOKIE_SECURE=false
```

| Variable | Descripción |
| --- | --- |
| `PORT` | Puerto del frontend; por defecto `3000`. |
| `API_BASE_URL` | URL base del backend, normalmente `http://127.0.0.1:5000/api`. |
| `SECRET_KEY` | Clave de Flask utilizada para proteger la sesión; **debe tener al menos 32 caracteres**. |
| `SESSION_COOKIE_SECURE` | En desarrollo local por HTTP suele ser `false`; en un despliegue HTTPS debe ser `true`. |
| `SUPER_ADMIN_EMAIL` | Correo configurado para identificar al administrador principal. |
| `MAIL_*` | Configuración de correo incluida en el archivo de ejemplo, según el despliegue. |

Podés generar una clave segura con:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Nunca subas el archivo `.env` ni claves, tokens o contraseñas al repositorio.**

### 4. Iniciar los servidores

Primero iniciá el **backend**, siguiendo las instrucciones del repositorio [Backend_Api](https://github.com/NahuelGz1/Backend_Api). Verificá su disponibilidad:

- [Estado del backend](http://127.0.0.1:5000/api/ping)

En otra terminal, desde la raíz de `Frontend-Web`, con el entorno virtual activado, ejecutá:

```bash
python app.py
```

Abrí **http://127.0.0.1:3000** en el navegador.

Los puertos y direcciones anteriores corresponden a la configuración local predeterminada; pueden cambiar según `.env`.

## Funcionalidades principales

### Clientes

- Inicio, cartelera, detalle de películas y próximos estrenos.
- Registro, inicio y cierre de sesión; recuperación y cambio de contraseña.
- Selección de función y butacas.
- Selección de servicios adicionales con comprobación del cupo de estacionamiento por función (**máximo 20 plazas**), actualización de cantidades y confirmación de compra.
- Consulta del perfil y del historial de compras; opciones de descarga y cancelación según las reglas del sistema.

### Administración

- Consulta de estadísticas y métricas.
- Gestión de películas, incluida la búsqueda externa mediante TMDB.
- Gestión de salas, funciones y servicios adicionales. Incluye cancelación administrativa de funciones con motivo, cálculo de devolución e intento de notificación por correo a los compradores.
- Gestión de permisos de otras cuentas administrativas, restringida al administrador principal.
- Consulta y validación de códigos QR.

> Algunas operaciones requieren autenticación o permisos de administrador; la lógica de negocio y las validaciones finales corresponden al backend.

## Estructura principal

```text
Frontend-Web/
├── app.py                 # Configuración de Flask, sesiones y registro de rutas
├── routes/                # Vistas para clientes, autenticación y administración
├── services/              # Comunicación con la API y lógica de presentación
│   └── api_client.py      # Cliente HTTP de Backend_Api
├── templates/             # Plantillas HTML/Jinja2
├── static/                # CSS, JavaScript e imágenes
├── instance/              # Datos locales de sesión (generados al ejecutar)
├── requirements.txt       # Dependencias de Python
├── .env.example           # Ejemplo de configuración local
├── .env.docker.example    # Ejemplo de configuración con Docker Compose
├── Dockerfile             # Imagen del frontend
├── compose.yaml           # Orquestación con backend y MySQL
├── DOCKER.md              # Guía completa de Docker
└── init.sh                # Preparación opcional del entorno
```

La aplicación se crea en `create_app()` de `app.py`. Las vistas se registran mediante *blueprints* y utilizan `services/api_client.py` para comunicarse con la API.

## Ejemplos de páginas

Con el frontend iniciado localmente:

| Ruta | Descripción |
| --- | --- |
| `/` | Página principal. |
| `/cartelera` | Catálogo de películas en cartelera. |
| `/registrarse` | Registro de clientes. |
| `/iniciar-sesion` | Inicio de sesión. |
| `/mi-perfil` | Perfil del usuario autenticado. |
| `/servicios` | Selección de servicios adicionales. |
| `/admin/estadisticas` | Panel de métricas para administradores. |
| `/admin/peliculas` | Gestión de películas para administradores. |
| `/admin/funciones` | Gestión de funciones para administradores. |

Las páginas de la compra pueden depender de datos guardados en la sesión, por lo que conviene recorrerlas desde la cartelera en lugar de abrir cada ruta directamente.

## Ejecutar con Docker Compose (opcional)

El repositorio incluye [`DOCKER.md`](DOCKER.md), con instrucciones para levantar **frontend, backend y MySQL** mediante Docker Compose. La disposición esperada de los repositorios es:

```text
Proyecto-Final/
├── Backend_Api/
└── Frontend-Web/
```

Seguí [`DOCKER.md`](DOCKER.md) para configurar `.env.docker`, construir los contenedores y administrar sus datos. **No elimines los volúmenes de MySQL** si querés conservar la base de datos.

## Problemas frecuentes

| Situación | Qué comprobar |
| --- | --- |
| El sitio no inicia y menciona `SECRET_KEY` | Que `.env` exista y contenga una clave de al menos 32 caracteres. |
| La página carga, pero no aparecen películas o funciones | Que `Backend_Api` esté ejecutándose y `API_BASE_URL` apunte a su `/api`. |
| Error de conexión con la API | Comprobar `http://127.0.0.1:5000/api/ping` y revisar los registros de ambos servidores. |
| La sesión no se mantiene | Revisar la configuración de cookies, el entorno HTTP/HTTPS y el almacenamiento de sesiones. |
| Un formulario requiere autenticación | Iniciar sesión con una cuenta válida y comprobar sus permisos. |

## Documentación relacionada

- [Backend_Api — API REST y configuración de MySQL](https://github.com/NahuelGz1/Backend_Api).
- [DOCKER.md — Ejecución del proyecto con Docker](DOCKER.md).
- [Issue #83 — Documentación técnica del proyecto](https://github.com/NahuelGz1/Backend_Api/issues/83).
- [Manual de API (OpenAPI 3.0)](https://github.com/NahuelGz1/Backend_Api/blob/develop/docs/Manual_API_Cine_paradiso.yaml), mantenido en el repositorio Backend_Api. El enlace funcionará una vez incorporado el Pull Request correspondiente a `develop`.

---

**Cine Paradiso** — Proyecto académico. Esta guía describe el entorno de desarrollo y no sustituye la configuración de seguridad necesaria para un despliegue en producción.
