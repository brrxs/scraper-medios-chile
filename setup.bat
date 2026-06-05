@echo off
echo ============================================
echo  Scraper de Prensa Chilena - Configuracion
echo ============================================
echo.

cd /d "%~dp0app"

echo [1/3] Creando entorno virtual...
python -m venv .venv
if errorlevel 1 (
    echo ERROR: No se pudo crear el entorno virtual.
    echo Asegurate de tener Python 3.10 o superior instalado.
    pause
    exit /b 1
)

echo [2/3] Instalando dependencias...
.venv\Scripts\pip install -r requirements.txt streamlit pandas --quiet
if errorlevel 1 (
    echo ERROR: Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

echo [3/3] Instalando navegador Chromium para Playwright...
.venv\Scripts\python -m playwright install chromium
if errorlevel 1 (
    echo ERROR: Fallo la instalacion de Playwright.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Listo. Ejecuta launch.bat para abrir la app.
echo ============================================
pause
