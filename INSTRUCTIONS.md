# prensa_chile_py — Instructions

Query-driven scraper for 15 Chilean news outlets. Given a keyword query and a date range it searches each outlet's native search endpoint, falls back to its category feed if search returns nothing, and writes results to structured CSV and Parquet files.

---

## Setup

```powershell
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate         # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browser (one-time, ~300 MB)
python -m playwright install chromium
```

**Requirements:** Python 3.10+. Tested on Python 3.13 / Windows 11.

---

## Usage

### `run` — scrape outlets

```powershell
# All 15 outlets, last 7 days (default)
python run.py run

# Keyword search across all outlets, last 30 days
python run.py run --query "reforma pensiones" --days 30

# Specific outlets only
python run.py run elsiglo emol elmostrador --query "pobreza" --days 14

# Custom date range
python run.py run --query "trabajo" --since 2026-04-01 --to 2026-04-30

# Run 6 outlets in parallel with a live progress table
python run.py run --query "salud" --days 7 --workers 6 --progress
```

**Flags:**

| Flag | Default | Description |
|---|---|---|
| `--query` / `-q` | none | Search phrase (AND within, OR across). Repeatable — see below. |
| `--days N` | 7 | Scrape the last N days |
| `--since YYYY-MM-DD` | 7 days ago | Start date (inclusive) |
| `--to YYYY-MM-DD` | today | End date (inclusive) |
| `--workers N` / `-w` | min(outlets, 4) | Parallel worker processes |
| `--progress` | off | Show a live `rich` table during scraping |

After each run a Markdown report is automatically written to `reports/report_YYYYMMDD_HHMMSS.md` with a per-outlet summary and any flags (missing dates, short bodies, errors, low yield).

#### Multi-query (parallel phrases)

Pass `--query` more than once to fan out across name variants. Within each phrase
words combine with **AND**; across phrases they combine with **OR**.

```powershell
# "Mara Sedini" (both words) OR just "Sedini" (alone)
python run.py run --query "Mara Sedini" --query "Sedini" --since 2026-03-11
```

The scraper runs the site's native search once per phrase, dedupes URLs, then
keeps any article whose title+body matches at least one phrase. The merge
command accepts the same repeated `--query` syntax and uses the same filter.

### `check` — smoke-test a single outlet

Fetches the listing page and one article, prints selector results and the parsed article. Does not save any data.

```powershell
python run.py check emol
python run.py check t13
```

### `list` — show all registered outlets

```powershell
python run.py list
```

---

## Outlet implementation details

| Slug | Type | Notes |
|---|---|---|
| `elsiglo` | HTML | WordPress |
| `elmostrador` | HTML | WordPress |
| `ciper` | HTML | Date extracted from canonical URL. WP `?s=` is single-term only — multi-word AND search returns 0; use parallel `--query` phrases. |
| `eldesconcierto` | HTML | Search is JS-rendered (Google CSE), disabled. Crawls 5 category index pages (~75 candidate URLs) and applies the query filter. |
| `elciudadano` | HTML | WordPress; OG meta date fallback |
| `biobio` | JSON API | Hidden API at `www.biobiochile.cl/lista/api/buscador` (same one the `datamedios` R package uses). |
| `cooperativa` | HTML | Prontus CMS search via `/cgi-bin/prontus_search.cgi` (form-submission target). Date extracted from canonical URL. |
| `cnnchile` | HTML | WordPress; search at `/buscador/{query}/page/{n}/` (slug-style path, needs `%20` not `+`). |
| `lanacion` | HTML | WordPress; slow site, 10 s timeout |
| `meganoticias` | HTML | WordPress; OG meta date fallback |
| `lacuarta` | HTML | Custom CMS |
| `emol` | JSON API | Hidden API at `newsapi.ecn.cl` |
| `t13` | Playwright | Homepage only (~54 URLs); no paginated listing |
| `24horas` | Playwright | Scroll-to-load; 8-page cap |
| `chvnoticias` | Playwright | Listing page only (~8 URLs) |

---

## Output

### Files

```
datos/
  {slug}/
    {slug}_YYYYMMDD_HHMMSS.csv      # UTF-8 CSV
    {slug}_YYYYMMDD_HHMMSS.parquet  # Parquet (columnar)

reports/
  report_YYYYMMDD_HHMMSS.md         # Auto-generated after each run

logs/
  scraping.log                      # Persistent run log
```

### Schema (8 fields)

| Field | Type | Description |
|---|---|---|
| `titulo` | string | Article headline |
| `cuerpo` | string | Body text (paragraphs joined with `\n`) |
| `bajada` | string | Subtitle / lead paragraph (if available) |
| `fecha` | YYYY-MM-DD | Publication date |
| `fuente` | string | Outlet slug |
| `url` | string | Canonical article URL |
| `fecha_scraping` | ISO datetime | When the article was scraped |
| `query` | string | The query used for this run |

---

## Design notes

- **Search-first strategy:** each outlet tries its native `/search?q=` endpoint first. With multi-query, each phrase runs an independent search and URLs are merged. If every phrase returns 0, falls back to the category feed + local keyword filter. Outlets with no working search (Playwright outlets, eldesconcierto) always use the feed.
- **Date-bound pagination:** stops paginating as soon as a page is entirely older than `--since`. Hard cap: 50 pages (8 for Playwright outlets).
- **Accent-insensitive matching:** `unicodedata.normalize('NFD')` so "reforma" matches "Reforma", "Reformá", etc.
- **Phrase semantics:** within a `--query` phrase, all words must be present (AND). Across multiple `--query` flags, any phrase matching keeps the article (OR).
- **Parallel execution:** uses `multiprocessing.Pool` (not threads) so Playwright's synchronous API is safe. Each worker process has its own browser instance.
- **Logging queue:** subprocess log records are funnelled back to the main process via `QueueHandler` / `QueueListener` so all output goes to `scraping.log` and stdout.

---

## Troubleshooting

**`python.exe` not found after copying to a new machine**
The `.venv` folder hardcodes the Python path. Delete it and recreate:
```powershell
Remove-Item -Recurse -Force .venv
python -m venv .venv
pip install -r requirements.txt
python -m playwright install chromium
```

**Playwright Chromium not installed**
```powershell
python -m playwright install chromium
```

**Outlet returns 0 articles**
Run `check` to verify selectors are still valid. Sites occasionally redesign their HTML:
```powershell
python run.py check <slug>
```

**NoDate articles in report**
The outlet's date element was not found or couldn't be parsed. The article is still saved but `fecha` will be empty. Check `reports/` for details and run `check` on the affected outlet.

**Slow outlets (lanacion, 24horas, elciudadano)**
These sites have slow servers or lazy-loading. Use `--workers` to run them in parallel with faster outlets:
```powershell
python run.py run --query "reforma" --days 7 --workers 4 --progress
```
