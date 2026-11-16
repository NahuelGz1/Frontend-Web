# Ejecutar Cine Paradiso con Docker

Esta configuración levanta el frontend, el backend y MySQL en contenedores.
La comunicación entre frontend y backend sigue realizándose en Python mediante
`requests`; el navegador no accede directamente al backend ni a MySQL.

## Requisitos

- Docker Desktop con Compose en Windows (con WSL 2 habilitado) o Linux; en Linux
  también se puede usar Docker Engine con el plugin Docker Compose.
- Los dos repositorios clonados como directorios hermanos:

  ```text
  Proyecto-Final/
  ├── Backend_Api/
  └── Frontend-Web/
  ```

- Docker debe tener acceso a esos directorios. En Docker Desktop habilitá el
  acceso a los archivos si es necesario.

## Primera ejecución

1. Abrí una terminal en `Frontend-Web` y copiá la configuración de ejemplo:

   ```bash
   # Linux, Git Bash o WSL
   cp .env.docker.example .env.docker
   ```

   En PowerShell:

   ```powershell
   Copy-Item .env.docker.example .env.docker
   ```

2. Editá `.env.docker`: reemplazá las dos contraseñas de MySQL y las claves
   `SECRET_KEY` y `JWT_SECRET_KEY` por valores diferentes y seguros. Las claves
   de la aplicación deben tener al menos 32 caracteres. Podés generar cada
   valor con Python: `python -c "import secrets; print(secrets.token_hex(32))"`.
   Usar valores hexadecimales evita problemas con caracteres especiales de
   Compose. No compartas ni subas `.env.docker` al repositorio.

3. Desde `Frontend-Web`, ejecutá:

   ```bash
   docker compose --env-file .env.docker up --build -d
   docker compose --env-file .env.docker ps
   ```

   La primera vez puede tardar varios minutos en descargar las imágenes,
   instalar dependencias e inicializar la base. Si algún servicio falla:

   ```bash
   docker compose --env-file .env.docker logs --tail=100
   ```

4. Abrí <http://localhost:3000>. El backend también está disponible desde la
   misma computadora en <http://localhost:5000/api/ping>. MySQL no publica un
   puerto en el anfitrión.

El puerto del frontend puede cambiarse con `FRONTEND_PORT` y el del backend
con `BACKEND_PORT` en `.env.docker`. Si cambiás el puerto del frontend,
actualizá también `FRONTEND_URL`.

## Datos y servicios externos

- MySQL usa el volumen `mysql_data`: los datos sobreviven a reinicios,
  reconstrucciones y `docker compose down`. El volumen es independiente de
  cualquier MySQL instalado en la computadora.
- Solo cuando el volumen está vacío, MySQL ejecuta `init_db.sql` y `seed.sql`
  del backend. El seed actual incluye películas, funciones, la cuenta
  administradora inicial y una compra de prueba para validar QR. Esos datos son
  de desarrollo; **no uses esta configuración ni esa cuenta de prueba como
  instalación de producción**. Los cambios posteriores a los scripts no se
  cargan automáticamente sobre un volumen existente.
- El backend aplica al arrancar sus migraciones automáticas con el usuario de
  aplicación. El script de creación ya no borra una base existente; ejecutarlo
  manualmente sobre tablas existentes puede fallar en lugar de reemplazarlas.
- `AUTO_SEED` está desactivado; la compra de prueba mencionada proviene de
  `seed.sql`, no del fixture de arranque.
- TMDB requiere `TMDB_API_KEY`. Para correos, configurá `MAIL_*` y/o `SMTP_*`
  según el servicio utilizado. Dentro del contenedor, `localhost` se refiere
  al propio contenedor, no a la computadora anfitriona.
- Las sesiones del frontend se guardan en el contenedor. Al recrearlo, los
  usuarios tendrán que iniciar sesión nuevamente.
- Las contraseñas de MySQL se aplican al inicializar un volumen nuevo. Cambiar
  `.env.docker` después no cambia los usuarios ya creados en la base: hay que
  actualizar las contraseñas también en MySQL.

## Acceso desde otro dispositivo

El puerto del frontend escucha en las interfaces del anfitrión. Para acceder
desde un celular o computadora de la misma red, usá
`http://IP_DEL_ANFITRION:3000` (o el puerto configurado) y permití el puerto en
el firewall. Configurá `FRONTEND_URL` con esa misma dirección para que los
enlaces de los correos funcionen desde el dispositivo.

Para acceso público necesitás configurar un dominio, HTTPS y un proxy inverso.
Con HTTPS, configurá `SESSION_COOKIE_SECURE=true`. Esta configuración es para
desarrollo y demostración: no incluye proxy, certificados, copias de seguridad
ni una configuración segura de producción.

## Operaciones habituales

Ejecutá estos comandos desde `Frontend-Web`:

```bash
# Ver logs
docker compose --env-file .env.docker logs -f

# Reconstruir después de cambiar código o dependencias
docker compose --env-file .env.docker up --build -d

# Detener sin borrar la base
docker compose --env-file .env.docker down
```

No uses `docker compose down -v` salvo que quieras eliminar **todos los datos**
del volumen de MySQL. Para conservar datos importantes, hacé una copia de
seguridad antes de cualquier operación sobre el volumen.
