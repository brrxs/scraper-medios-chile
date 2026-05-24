# prensa_chile_py

Keyword scraper for Chilean online news, built for the **Monitor Social** project at Pontificia Universidad Católica de Chile. Given a search query and date range, it retrieves articles from 15 outlets spanning print-digital, broadcast, investigative, and alternative media.

Full setup and usage documentation: [INSTRUCTIONS.md](INSTRUCTIONS.md).

---

## What it does

The scraper takes a keyword query (e.g. `"reforma pensiones"`) and a date window and returns a structured dataset of articles — headline, body, date, source, URL — across all configured outlets. It uses each site's native search endpoint where available, and falls back to crawling category feeds with local keyword filtering where it is not.

Output is written to CSV and Parquet files under `datos/`, one subfolder per outlet.

---

## Media coverage

15 outlets covering the main segments of Chile's national news media landscape.

### Print-digital (legacy press with online presence)

| Outlet | Slug | Profile |
|---|---|---|
| **Emol** | `emol` | Digital arm of *El Mercurio*, Chile's largest and oldest newspaper. Center-right, business and politics focus. Reaches a broad middle-to-upper-class readership. |
| **La Cuarta** | `lacuarta` | Popular tabloid from the *El Mercurio* group. Crime, sports, entertainment. Working-class readership. |
| **La Nación** | `lanacion` | Historically state-linked newspaper, now privately operated. Centrist. Lower traffic than major outlets. |

### Broadcast media (TV and radio)

| Outlet | Slug | Profile |
|---|---|---|
| **T13** | `t13` | Canal 13's digital news arm. Center, originally Catholic University-affiliated. One of Chile's most established TV channels. |
| **24 Horas** | `24horas` | TVN's news portal. Chile's public television broadcaster, legally required to reflect pluralism. |
| **CHV Noticias** | `chvnoticias` | Chilevisión news. Owned by Warner Bros. Discovery. General-audience TV, tabloid-leaning coverage. |
| **Mega Noticias** | `meganoticias` | Mega TV news. Large commercial broadcaster, general audience, popular crime and social coverage. |
| **Cooperativa** | `cooperativa` | Radio Cooperativa's digital news. One of Chile's oldest and most respected radio stations. Centrist, strong political coverage, wide reach across demographics. |
| **CNN Chile** | `cnnchile` | Chilean franchise of CNN. Center, 24-hour news cycle, political and economic focus. |

### Digital natives

| Outlet | Slug | Profile |
|---|---|---|
| **El Mostrador** | `elmostrador` | Founded 2000, one of Chile's first major online-only outlets. Center-left, opinion-heavy, strong political and economic coverage. |
| **BioBio Chile** | `biobio` | One of Chile's largest digital-native outlets by traffic. Regional origins (Biobío region) but national coverage. General news, crime, popular topics. |

### Investigative / independent

| Outlet | Slug | Profile |
|---|---|---|
| **CIPER Chile** | `ciper` | Centro de Investigación Periodística. Non-profit investigative journalism. No editorial line — publishes deep investigations into corruption, health, justice. High credibility. |

### Left and alternative press

| Outlet | Slug | Profile |
|---|---|---|
| **El Siglo** | `elsiglo` | Newspaper linked to the Communist Party of Chile. Labor, social movements, political left. |
| **El Desconcierto** | `eldesconcierto` | Left-leaning digital outlet. Social movements, feminism, environmentalism, youth politics. |
| **El Ciudadano** | `elciudadano` | Alternative left-wing digital outlet. Community, indigenous rights, anti-establishment politics. |

---

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
