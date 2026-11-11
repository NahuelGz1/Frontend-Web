#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "=== 1. Verificando entorno virtual ==="
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ] && [ -d "venv" ]; then
    VENV_DIR="venv"
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "No existe el entorno virtual ($VENV_DIR). Creando..."
    python3 -m venv "$VENV_DIR"
else
    echo "Ya existe el entorno virtual ($VENV_DIR)"
fi

echo "=== 2. Activando entorno virtual ==="
source "$VENV_DIR/bin/activate"

echo "=== 3. Actualizando pip ==="
pip install --upgrade pip

echo "=== 4. Instalando dependencias de requirements.txt ==="
pip install -r requirements.txt

echo "=== 5. Verificando archivo de variables de entorno (.env) ==="
if [ ! -f ".env" ]; then
    echo "No existe archivo '.env'. Creando a partir de '.env.example'..."
    cp .env.example .env
    echo "Asegúrate de revisar el archivo '.env' antes de iniciar la app."
else
    echo "Ya existe el archivo '.env', no se modifica ninguna configuracion"
fi

echo "=== ¡Inicializacion completada con exito! ==="
