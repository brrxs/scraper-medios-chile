# prensa_chile_py

Keyword scraper for Chilean online news, built for personal use. Given a search query and date range, it retrieves articles from 15 outlets and Google News, spanning print-digital, broadcast, investigative, and alternative media.

Full setup and usage documentation: [INSTRUCTIONS.md](INSTRUCTIONS.md).

---

## What it does

The scraper takes a keyword query (e.g. `"reforma pensiones"`) and a date window and returns a structured dataset of articles — headline, body, date, source, URL — across all configured outlets. It uses each site's native search endpoint where available, and falls back to crawling category feeds with local keyword filtering where it is not.

Output is written to CSV and Parquet files under `datos/`, one subfolder per outlet.

---

## Media coverage

15 outlets covering the main segments of Chile's national news media landscape.
| Outlet | Slug | URL | Type |
|---|---|---|---|
| Biobío Chile | `biobio` | biobiochile.cl | Radio/Digital |
| CHV Noticias | `chvnoticias` | chilevision.cl | Broadcast (TV) |
| CIPER Chile | `ciper` | ciperchile.cl | Investigative |
| CNN Chile | `cnnchile` | cnnchile.com | Broadcast (TV) |
| Cooperativa | `cooperativa` | cooperativa.cl | Radio/digital |
| El Ciudadano | `elciudadano` | elciudadano.com | Alternative |
| El Desconcierto | `eldesconcierto` | eldesconcierto.cl | Alternative |
| El Mostrador | `elmostrador` | elmostrador.cl | Digital |
| El Siglo | `elsiglo` | elsiglo.cl | Alternative |
| Emol | `emol` | emol.com | Print-digital |
| La Cuarta | `lacuarta` | lacuarta.com | Print-digital |
| La Nación | `lanacion` | lanacion.cl | Print-digital |
| Mega Noticias | `meganoticias` | meganoticias.cl | Broadcast (TV) |
| T13 | `t13` | t13.cl | Broadcast (TV) |
| 24 Horas | `24horas` | 24horas.cl | Broadcast (TV) |
| Google News | `google_news` | news.google.com | Search engine | 

## Output schema

Each article record has 8 fields:

| Field | Description |
|---|---|
| `titulo` | Headline |
| `cuerpo` | Body text |
| `bajada` | Subtitle / lead (when available) |
| `fecha` | Publication date (YYYY-MM-DD) |
| `fuente` | Outlet slug |
| `url` | Canonical article URL |
| `fecha_scraping` | Timestamp of when the article was collected |
| `query` | The search query used |

---

## Quick start

```powershell
# Setup (one time)
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium

# Scrape all outlets, last 7 days
python run.py run --query "reforma pensiones" --days 7 --progress
```

See [INSTRUCTIONS.md](INSTRUCTIONS.md) for full flag reference, multi-query syntax, troubleshooting, and design notes.

---

## Acknowledgments

This project builds directly on the following work:

- **[datamedios](https://socialtec-cl.github.io/datamedios/)** (socialtec-cl) — R package for Chilean media data. The hidden JSON search APIs used by Biobío and Emol were discovered through its source code; the offset and pagination logic mirrors its implementation.

- **[prensa_chile](https://github.com/bastianolea/prensa_chile)** (Bastián Olea) — Prior scraper for Chilean press that shaped the outlet selection and overall approach.

- **[GNews](https://github.com/ranahaani/GNews)** (ranahaani) — Library wrapping Google News RSS. Powers the `google_news` outlet with Chile/Spanish targeting.

- **[trafilatura](https://trafilatura.readthedocs.io/en/latest/)** — Article extraction library used to retrieve and clean full article bodies across outlets.
