<div align="center">
  <img src="app/style-kit/assets/logo.svg" alt="PressCL" width="140">
  <h1>PressCL</h1>
  <p>Aplicación para buscar noticias en medios chilenos</p>
</div>

<a href="https://doi.org/10.5281/zenodo.20563693"><img src="https://zenodo.org/badge/1259735009.svg" alt="DOI"></a>


> **Estado:** Proyecto personal, en uso activo pero sin mantenimiento activo. Issues bienvenidos; PRs revisados según disponibilidad. Los selectores de medios pueden romperse cuando los sitios rediseñan su HTML.

Aplicación web para buscar archivos de noticias chilenas. Ingresa una palabra clave y un rango de fechas, elige tus medios y descarga un dataset estructurado, sin necesidad de programar.

Documentación completa: [INSTRUCTIONS.md](app/INSTRUCTIONS.md)

<img src="app/style-kit/presscl.gif" alt="PressCL demo" width="700">


Si usas PressCL en tu investigación o trabajo, por favor cítalo de la siguiente manera:

> Barrientos, T. (2026). *PressCL: Aplicación para buscar noticias en medios chilenos* (v0.3). Zenodo. https://doi.org/10.5281/zenodo.20563693

---

## Descargas

**Última versión: [PressCL v0.3](https://github.com/brrxs/PressCL/releases/tag/v0.3)**

1. Descarga el archivo `PressCL-v0.3.zip`
2. Extrae la carpeta donde quieras tener la app
3. Haz doble clic en `setup.bat` (solo la primera vez)
4. Haz doble clic en el acceso directo **PressCL**

Todas las versiones: [github.com/brrxs/PressCL/releases](https://github.com/brrxs/PressCL/releases)

**Requisitos:** Python 3.10 o superior. Descargar desde [python.org](https://www.python.org/downloads/) marcando la opción "Add Python to PATH".

---

## Cómo funciona

Abre la app en el navegador, escribe una consulta (por ejemplo, `reforma pensiones`), define un rango de fechas y presiona ejecutar. PressCL busca simultáneamente en 15 medios chilenos y devuelve una tabla de artículos (título, cuerpo, fecha, fuente, URL) lista para descargar como CSV o Parquet.

Internamente, usa el endpoint de búsqueda nativo de cada sitio cuando está disponible, y recurre a crawling de feeds de categorías con filtro local cuando no lo está.


---

## Instalación (Windows)

**Requisitos:** Python 3.10 o superior. Descargar desde [python.org](https://www.python.org/downloads/) marcando la opción "Add Python to PATH".

1. Descarga o clona este repositorio
2. Haz doble clic en `setup.bat` y espera a que termine (descarga Chromium, ~300 MB, solo la primera vez)
3. Haz doble clic en el acceso directo **PressCL** que aparece
4. La app se abre automáticamente en el navegador

Sin terminal, sin comandos.


---

## Medios disponibles

16 medios que cubren los principales segmentos del panorama noticioso chileno.

| Medio | URL | Tipo |
|---|---|---|
| Biobío Chile | biobiochile.cl | Radio/Digital |
| CHV Noticias | chilevision.cl | Televisión |
| CIPER Chile | ciperchile.cl | Investigación |
| CNN Chile | cnnchile.com | Televisión |
| Cooperativa | cooperativa.cl | Radio/Digital |
| El Ciudadano | elciudadano.com | Alternativo |
| El Desconcierto | eldesconcierto.cl | Alternativo |
| El Mostrador | elmostrador.cl | Digital |
| El Siglo | elsiglo.cl | Alternativo |
| Emol | emol.com | Prensa digital |
| La Cuarta | lacuarta.com | Prensa digital |
| La Nación | lanacion.cl | Prensa digital |
| Mega Noticias | meganoticias.cl | Televisión |
| T13 | t13.cl | Televisión |
| 24 Horas | 24horas.cl | Televisión |
| Google News | news.google.com | Buscador |


---

## Datos de salida

Cada artículo incluye 8 campos:

| Campo | Descripción |
|---|---|
| `titulo` | Titular |
| `cuerpo` | Cuerpo del artículo |
| `bajada` | Bajada / entradilla (cuando está disponible) |
| `fecha` | Fecha de publicación (YYYY-MM-DD) |
| `fuente` | Medio |
| `url` | URL del artículo |
| `fecha_scraping` | Fecha y hora de recolección |
| `query` | Consulta utilizada |


---

## Uso responsable

PressCL está diseñado para uso periodístico e investigativo sobre contenido de acceso público.

- Las solicitudes están limitadas a 1,5–3,5 segundos entre páginas por medio.
- El scraping está limitado a 50 páginas por búsqueda.
- El usuario es responsable de cumplir con los términos de uso de cada medio.
- Esta herramienta no sortea paywalls ni accede a contenido restringido.


---

## Créditos

- **[datamedios](https://socialtec-cl.github.io/datamedios/)** (socialtec-cl): Paquete R para datos de medios chilenos. Las APIs JSON ocultas de Biobío y Emol fueron descubiertas a través de su código fuente.
- **[prensa_chile](https://github.com/bastianolea/prensa_chile)** (Bastián Olea): Scraper previo de prensa chilena que definió la selección de medios y el enfoque general.
- **[GNews](https://github.com/ranahaani/GNews)** (ranahaani): Librería que envuelve el RSS de Google News. Alimenta el medio `google_news` con targeting Chile/español.
- **[trafilatura](https://trafilatura.readthedocs.io/en/latest/)**:  Librería de extracción de artículos para obtener y limpiar el cuerpo de los textos.


---

## Para desarrolladores

Si quieres usar el CLI, agregar medios o entender el código interno, revisa [INSTRUCTIONS.md](app/INSTRUCTIONS.md) y [CONTRIBUTING.md](CONTRIBUTING.md).


---

## Licencia

[MIT](LICENSE)
