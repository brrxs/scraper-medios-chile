# prensa_chile_py — Project Progress

**Project:** Monitor Social @ UC Chile — Chilean news scraper (Python)
**Started:** 2026-05-20 | **Last updated:** 2026-05-27 (Google News → GNews library)

---

## 2026-05-27 — Google News backend switched to GNews library

The previous `feedparser`-direct implementation hit HTTP 503 (IP-based rate limit) after the first scrape,
making repeated runs unreliable.

### What changed
- `scraper/outlets/google_news.py` rewritten to use the **GNews** library (ranahaani/GNews).
- Same underlying RSS mechanism but adds: Chile/Spanish targeting (`gl=CL`, `hl=es-419`), automatic
  Google redirect URL resolution (removes the custom `_resolve_url` HEAD/GET workaround), and optional proxy support.
- **Retry with exponential backoff**: 3 attempts per day-window fetch (5 → 15 → 30s + ±2s jitter).
  Handles transient 503s without crashing the run.
- **Polite inter-day delay**: 1–2.5s sleep between day-window calls.
- **`fuente` now shows actual outlet name** (e.g. `"El Mostrador"`) instead of flat `"google_news"`.
- **Proxy support**: set `$env:GNEWS_PROXY = "http://user:pass@host:port"` to route through a proxy
  if Google blocks the IP persistently.
- `gnews>=0.3.7` added to `requirements.txt`.

### Files changed
`scraper/outlets/google_news.py` (full rewrite), `requirements.txt`, `progress.md`

### After update — install new dependency
```powershell
.venv\Scripts\Activate.ps1
pip install gnews
```

---

## 2026-05-26 — Google News catch-all source added

- New outlet `google_news` (type: RSS) added as a 16th supplementary source.
- Uses Google News RSS (`https://news.google.com/rss/search`) via `feedparser`. No API key required.
- Respects `--since`/`--days` window via `after:`/`before:` RSS operators passed in the query string.
- Redirect URLs resolved to actual outlet URLs via HEAD (+ GET fallback) for cross-outlet dedup in `_cmd_merge`.
- `cuerpo` stores the RSS summary (no full-text — supplementary coverage use case). ShortBody warning suppressed for this outlet only in `report.py`.
- New dependency: `feedparser>=6.0.0` added to `requirements.txt`.

### Files changed
scraper/outlets/google_news.py (new), scraper/outlets/__init__.py, requirements.txt, scraper/report.py, progress.md

---

## 2026-05-22 audit (Round 2) — search for 24horas/t13/chv + selector fixes

### Outlets fixed

| Outlet | Before | After | Key change |
|---|---|---|---|
| `24horas` | No search (Playwright listing only) | Prontus CGI search via `/cgi-bin/prontus_search.cgi` (requests, not PW) | 60 results for "sedini" across 4 pages; link_selector broadened from `/nacional/` to `/actualidad/` |
| `t13` | Homepage only (~52 URLs, no search) | Added `SEARCH_URL_TEMPLATE = "https://www.t13.cl/search?q={query}&page={page}"` | Search endpoint confirmed working |
| `chvnoticias` | Listing page only (~8 URLs, no search) | Added `/search/{query}/page/{n}/` endpoint + `_encode_query` using `%20` | Feed link_selector broadened from `/nacional/` to `/noticias/` |
| `elmostrador` | `h2.d-main-card__title a` (feed-only layout) | `a[href*='elmostrador.cl/noticias/'][href*='/20']` | Now works on both feed and `?s=` search results; 72 URLs on page 1 |
| `meganoticias` | `a[href*='/nacional/']` (restricted to national section) | `a[href*='meganoticias.cl/'][href$='.html']` | Captures articles from any section; 11 URLs on page 1 |
| `eldesconcierto` | 5 category pages, no pagination (~75 candidates) | Paginate each category up to 3 pages (~225 candidates) | Stop condition: 0 links on page → stop that category |
| `lacuarta` | `/?s=` search (returns homepage, broken) + `/category/cronica/` only | Search disabled; crawl `/category/cronica/` AND `/chile/` sections | Found Mara Sedini article on first check; `/chile/` section has political coverage |

### Files changed (Round 2)

scraper/outlets/horas24.py, scraper/outlets/t13.py, scraper/outlets/chvnoticias.py,
scraper/outlets/elmostrador.py, scraper/outlets/meganoticias.py,
scraper/outlets/eldesconcierto.py, scraper/outlets/lacuarta.py, progress.md

### 24horas Prontus CGI params (confirmed live)

```python
_SEARCH_DEFAULTS = {
    "search_prontus": "24horas",
    "search_tmp": "search.html",
    "search_modo": "and",
    "search_orden": "cro",
    "search_form": "no",
    "search_resxpag": "15",
}
```

### All 7 outlets check-verified (2026-05-22)

| Outlet | check result |
|---|---|
| elmostrador | 72 URLs found, article parsed OK (6101 chars) |
| meganoticias | 11 URLs found, article parsed OK (2674 chars) |
| 24horas | 90 feed URLs, article parsed OK; Prontus search: 60 results for "sedini" |
| eldesconcierto | 51 URLs found, article parsed OK |
| lacuarta | 6 URLs found, article parsed OK (first article was a Mara Sedini piece) |
| t13 | 52 URLs found, article parsed OK |
| chvnoticias | 8 URLs found, article parsed OK |

---

## 2026-05-22 audit — multi-query + 4 endpoint fixes

Triggered by low-recall observation on the "Mara Sedini" baseline (25 articles
across 5 outlets, vs. ~300+ expected). Two architectural changes and four
endpoint repairs, all live-tested.

### Architectural

- **Multi-query CLI**: `--query` is now `action="append"`. Phrase = AND of its
  words; across phrases = OR. Example: `--query "Mara Sedini" --query "Sedini"`
  runs two independent searches per outlet, dedupes URLs, then keeps any
  article that matches at least one phrase. `_cmd_merge` filter aligned to the
  same semantics (it was AND-all-terms-across-the-whole-query — inconsistent
  with the scraper, which used OR-any-term).
- New `scraper/utils.py` helpers: `phrase_matches` (AND within), `any_phrase_matches` (OR across). Replaces `matches_query`.
- `BaseScraper.run` / `BaseApiScraper.run` / `BasePlaywrightScraper.run` all
  signature-changed to `queries: list[str]`. The `query` column now stores
  the comma-joined phrase list.
- `_collect_urls_search` warns if page-1 returns 0 links — stops silent
  "search broken, falling back" failures from going unnoticed.
- New `_encode_query` hook (defaults to `quote_plus`); cnnchile overrides to
  `quote` so slug-style paths get `%20` instead of `+`.

### Endpoint repairs

| Outlet | Before | After | Yield Δ (Mara Sedini, 73 days) |
|---|---|---|---|
| `biobio` | HTML `/buscador/?q=` returned 0 (JS-rendered) | JSON API `/lista/api/buscador?offset=&search=&intervalo=&orden=ultimas` (same one `datamedios` R uses) | 6 → 181 |
| `cnnchile` | `/?s={q}&paged={n}` (WP default, returns ~5) | `/buscador/{q}/page/{n}/` with `%20` encoder | 5 → 51 |
| `cooperativa` | `/buscar/{q}/page/{n}` (HTTP 404, silent fallback to feed) | `/cgi-bin/prontus_search.cgi` with full hidden-form param bundle | 7 → 78 |
| `eldesconcierto` | `/?s={q}` (returned homepage, silent fallback to 3-URL feed) | Search disabled (Google CSE, JS-rendered, no headless path). Feed expanded to crawl 5 category indexes (~75 URLs) | 1 → 4 |

Total: 25 → 318 articles across the 5 affected outlets (~13×). ciper went 6→4
because its WordPress search literally returns 0 for any multi-word query
(`?s=Mara+Sedini` and `?s=Mara%20Sedini` both empty) — single-word
`?s=Sedini` returns 5 unique URLs (4 pass title/body validation). Workaround:
add a third `--query "Mara"`.

### Files changed

scraper/utils.py, scraper/base.py, scraper/base_api.py, scraper/base_playwright.py,
scraper/outlets/cnnchile.py, scraper/outlets/biobio.py,
scraper/outlets/cooperativa.py, scraper/outlets/eldesconcierto.py,
scraper/report.py, run.py, README.md.

### Out of scope (deliberate)

- `chvnoticias`: structural feed limit (~8 URLs from listing page). No working
  search endpoint found (`chilevision.cl/buscador?q=` → 404).
- Migrating `ciper` to its WP REST API (`/wp-json/wp/v2/posts?search=`) — user
  chose to keep the HTML scraper.

---

## What this project does

Query-driven scraper for 15 Chilean news outlets. Given a keyword query and a date range, it:
1. Tries each outlet's native search endpoint first
2. Falls back to the category feed + local keyword filter if search returns 0 results
3. Writes results to `datos/{slug}/{slug}_YYYYMMDD_HHMMSS.csv` and `.parquet`

**Usage:**
```powershell
$base = "c:\Users\Tomas\OneDrive - Universidad Católica de Chile\Monitor Social\BO\prensa_chile_py"
$py = "$base\.venv\Scripts\python.exe"
& $py "$base\run.py" run --query "reforma" --days 30 --workers 4 --progress
& $py "$base\run.py" run elsiglo emol --query "pobreza" --since 2026-05-01
& $py "$base\run.py" list
& $py "$base\validate.py"
# Auto-report written to reports/report_YYYYMMDD_HHMMSS.md after every run
```

---

## Current project state

### File structure
```
prensa_chile_py/
├── run.py                       CLI: run / list / check subcommands
├── validate.py                  Schema conformance checker (reads all CSVs in datos/)
├── requirements.txt             requests, beautifulsoup4, lxml, pyarrow, playwright (>= ranges)
├── .gitignore
├── scraper/
│   ├── base.py                  BaseScraper — HTML template-method scraper (requests)
│   ├── base_api.py              BaseApiScraper — JSON API scraper
│   ├── base_playwright.py       BasePlaywrightScraper — JS-rendered sites (headless Chromium)
│   ├── utils.py                 Spanish date parser, accent normalizer, text cleaner
│   ├── output.py                CSV + Parquet writer (datos/{slug}/)
│   └── outlets/
│       ├── __init__.py          REGISTRY dict: slug -> class
│       ├── elsiglo.py           El Siglo (WordPress)
│       ├── elmostrador.py       El Mostrador (WordPress)
│       ├── ciper.py             CIPER Chile (WordPress, investigative)
│       ├── eldesconcierto.py    El Desconcierto (no pagination, listing only)
│       ├── elciudadano.py       El Ciudadano (WordPress, homepage pagination)
│       ├── biobio.py            Radio Biobío (custom CMS)
│       ├── cooperativa.py       Cooperativa (date from canonical URL)
│       ├── cnnchile.py          CNN Chile
│       ├── lanacion.py          La Nación (WordPress)
│       ├── meganoticias.py      Meganoticias
│       ├── lacuarta.py          La Cuarta
│       ├── t13.py               T13 — Playwright, homepage only
│       ├── horas24.py           24 Horas — Playwright, scroll to load, /p/{n} pagination
│       ├── chvnoticias.py       CHV Noticias — Playwright, listing page only
│       └── emol.py              Emol (JSON API via newsapi.ecn.cl)
├── scraper/
│   └── report.py                Auto-report generator (called after every run)
├── datos/                       Output: one subfolder per outlet
├── reports/                     Auto-generated Markdown reports (one per run)
├── report.md                    Manual project-state report (updated 2026-05-22)
├── README.md                    Usage guide
└── logs/
```

---

## Outlets status

| Slug | Type | Live tested | Result | Notes |
|---|---|---|---|---|
| `elsiglo` | HTML | YES | 8 articles (2026-05-20) | Fully working |
| `emol` | JSON API | YES | 6 articles (2026-05-20) | Fully working |
| `ciper` | HTML | YES | 5 articles (2026-05-20) | Date from canonical URL |
| `elmostrador` | HTML | YES | 26 articles (2026-05-20) | Fully working |
| `biobio` | HTML | YES | 2 articles (2026-05-20) | Search returns 0 → fell back to feed+filter; low yield |
| `t13` | Playwright | YES | 4 articles (2026-05-21) | Homepage-only, no pagination |
| `24horas` | Playwright | YES | 1 article (2026-05-21) | PW_PAGE_CAP=8; dedup early-exit fix applied |
| `chvnoticias` | Playwright | YES | 1 article (2026-05-21) | Low yield — listing shows ~8 URLs |
| `cooperativa` | HTML | YES | 4 articles (2026-05-21) | Body selector fixed: `.cuerpo-articulo p` |
| `eldesconcierto` | HTML | YES | 1 article (2026-05-21) | Low yield — 3 URLs on listing, no pagination |
| `elciudadano` | HTML | YES | 60 articles (2026-05-21) | NoDate fixed: OG meta + URL fallback chain added |
| `cnnchile` | HTML | YES | 12 articles (2026-05-21) | Fully working |
| `lanacion` | HTML | YES | 9 articles (2026-05-21) | Slow site; `REQUEST_TIMEOUT=10` override added |
| `meganoticias` | HTML | YES | 58 articles (2026-05-21) | NoDate fixed: OG meta + URL fallback chain added |
| `lacuarta` | HTML | YES | 27 articles (2026-05-21) | Fully working |

**Validation result (2026-05-21, query="reforma", 7–30 days, all 15 outlets):**
- 224/224 articles passed schema validation — 100% pass rate
- 19 articles were missing date (elciudadano 12, meganoticias 7) — **fixed 2026-05-22** with OG meta + URL fallback

---

## Known bugs and fixes applied

| Bug | Fix | Status |
|---|---|---|
| `pyarrow==16.1.0` no wheel for Python 3.13 | Changed requirements.txt to `>=` ranges | Fixed |
| `UnicodeEncodeError` on Windows (cp1252) — `→` char in log message | Replaced `→` with `->` in `output.py:31` | Fixed |
| Biobio date format "Miércoles 20 mayo de 2026 \| 15:03" not parsed | Added weekday-strip + pipe-split pattern to `utils.py` | Fixed |
| Cooperativa `/noticias/` returns 168-char meta-refresh | Corrected URL to `/noticias/pais/` | Fixed |
| CIPER link selector typo | Their HTML has `alticle-link` (not `article-link`), matched intentionally | Fixed |
| elmostrador, eldesconcierto, biobio: wrong index URLs (404) | Corrected to live URLs after `check` verification | Fixed |
| t13, 24horas, chvnoticias: JS-rendered, 0 articles with `requests` | Rebuilt as `BasePlaywrightScraper` (headless Chromium) | Fixed |
| `run.py` log file path relative to cwd, not script dir | Changed to `Path(__file__).parent / "logs" / "scraping.log"` | Fixed |
| CHV `datetime` attribute contains wrong dates | Override `_date_text` to use visible text; collapse newlines with `re.sub` | Fixed |
| 24horas listing page lazy-loads cards | Override `_collect_urls_feed` to scroll before extracting links | Fixed |
| 24horas hung for 10+ min (HARD_PAGE_CAP=50 × Playwright loads) | Added `PW_PAGE_CAP=8`; dedup early-exit when no new URLs per page | Fixed |
| Cooperativa body selector `article p` returned <400 chars (3 elements) | Changed to `.cuerpo-articulo p` (19 elements, 4225 chars) | Fixed |
| Lanacion hangs on slow connections (default 20s timeout × many pages) | Added `REQUEST_TIMEOUT=10` override in `lanacion.py` | Fixed |
| venv hardcoded to `tomas.barrientos` Python path (different machine) | Rebuilt venv with `py` (Python 3.13.5) on new machine | Fixed |
| elciudadano + meganoticias: 19 articles with no date | Added `_date_text` override with OG meta → `datetime` attr → visible text → URL path fallback chain | Fixed |
| base_api.py: duplicate `_parse_date_str` duplicating `utils.parse_date` | Removed `_parse_date_str`, imported `parse_date` directly | Fixed |
| base_playwright.py: Playwright `ctx` could leak on `new_context()` exception | Moved `ctx = None` before try, guarded `ctx.close()` | Fixed |
| base.py: dead early-exit check at line 106 (unreachable) | Removed | Fixed |
| meganoticias link_selector too broad (second clause `article a[href]`) | Narrowed to `a[href*='/nacional/']` | Fixed |
| horas24 `_extract_links`: dead dual href check | Simplified to `full = href if startswith("http") else base + href` | Fixed |
| Outlets compiled regex inside methods on every call | Moved to module-level constants in ciper, cooperativa, chvnoticias | Fixed |
| Outlets ran sequentially — 15-outlet run took 1+ hour | Replaced for-loop with `multiprocessing.Pool` + `--workers` flag | Fixed |
| No live progress during scraping | Added `rich.Live` table with per-outlet status via `--progress` flag | Fixed |
| No automatic run report | Added `scraper/report.py` — Markdown report written to `reports/` after every run | Fixed |
| No documentation | Added `README.md` with setup, usage, outlet table, design notes, troubleshooting | Fixed |

---

## Playwright-specific notes (t13, 24horas, chvnoticias)

- **t13**: Homepage (`https://www.t13.cl/`) has ~54 article links. No working paginated listing URL exists (`/ultimas-noticias/page/{n}` is 404). Homepage-only fetch is enough for 7–30 day windows.
- **24horas**: Listing page lazy-loads articles; must scroll before extracting links. Pagination uses `/p/{n}` format (not `?page=` or `/page/`). Link depth filter needed to exclude category-only hrefs.
- **chvnoticias**: `time[datetime]` attribute is wrong (shows old dates from their CMS). Must parse date from visible text "DD/MM/YYYY..." — but text contains newlines; collapse with `re.sub(r'\s+', '', ...)` before parsing.
- All three use `SEARCH_URL_TEMPLATE = ""` — no search endpoint found; will always fall back to feed + keyword filter.
- Playwright browser launches once per `run()` call, shared across all page fetches.

---

## What still needs to be done

### Priority 1 — DONE (2026-05-21)
t13 (4), chvnoticias (1), 24horas (1) — all live-tested and validated.

### Priority 2 — DONE (2026-05-21)
All 7 HTML outlets live-tested: cooperativa (4), eldesconcierto (1), elciudadano (60), cnnchile (12), lanacion (9), meganoticias (58), lacuarta (27).

### Priority 3 — DONE (2026-05-22)
NoDate fix applied to elciudadano and meganoticias. OG meta → datetime attr → visible text → URL path fallback chain.

### Priority 4 — DONE (2026-05-22)
Parallelism, live progress (`--progress`), auto-report, README all implemented and verified.

### Pending — UX improvements (2026-05-27)

- **Dataset filenames**: current pattern `{slug}_{YYYYMMDD}_{HHMMSS}.csv` is hard to read at a glance — make them more descriptive/human-friendly (e.g. include query and date range).
- **Prettier log output**: the plain `[INFO]` log format is hard to scan — improve formatting (colours, structured layout, or cleaner timestamp style).

### Pending — Merging improvements (2026-05-27)

-**Merge**: with the addition of google news, the merge is outdate. GN has a unique format that needs to be harmonised with the rest. The cuerpo and bajada seems part of the same, consider merging it. a recurrent problem is the recurrent names of the outlets in the cuerpo and bajada section,. They're dennoted the following way: [OutletName]. Was thinking of merging into the same column the cuerpo and bajada and definig the name of the outlet form the [] name

### Status: PRODUCTION READY (2026-05-22)
All 15 outlets working. Parallel execution, live progress, auto-reports, and README in place.
NoDate fix verified — new runs produce 0 NoDate for all outlets.

```powershell
$base = "c:\Users\Tomas\OneDrive - Universidad Católica de Chile\Monitor Social\BO\prensa_chile_py"
$py = "$base\.venv\Scripts\python.exe"
& $py "$base\run.py" run --query "YOUR_QUERY" --days 30 --workers 4 --progress
& $py "$base\validate.py"
# Auto-report written to reports/report_YYYYMMDD_HHMMSS.md
```

---

## How to run from scratch on a new machine

```powershell
# 1. Navigate to project
cd "c:\path\to\prensa_chile_py"

# 2. Create venv
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install deps
pip install -r requirements.txt

# 4. Install Playwright browser (one-time)
python -m playwright install chromium

# 5. Smoke test (HTML + API + Playwright)
python run.py check elsiglo
python run.py check emol
python run.py check t13

# 6. First scrape
python run.py run elsiglo emol elmostrador ciper biobio --query "tu_tema" --days 7

# 7. Validate output
python validate.py
```

**Python version:** 3.13 (tested). Minimum: 3.10 (uses `list[dict]` type hints without `from __future__`).
**OS:** Windows 11. Should work on Linux/macOS with no changes.

---

## Design decisions worth knowing

- **Three scraper base classes**: `BaseScraper` (requests, for static HTML), `BaseApiScraper` (JSON APIs), `BasePlaywrightScraper` (headless Chromium, inherits from `BaseScraper`, only overrides `_fetch`).
- **Search-first strategy**: each outlet tries its native `/search?q=` endpoint; if page 1 returns 0 links, falls back to the category index feed + local keyword filter. Playwright outlets have no search URL — always fall back.
- **Date-bounded pagination**: stops paginating as soon as a full page of articles is older than `--since`. Never relies on a page count. Safety cap: `HARD_PAGE_CAP = 50`.
- **Emol uses a hidden JSON API** (`newsapi.ecn.cl`) discovered in the `datamedios` R package — no HTML parsing needed for Emol.
- **Accent-insensitive matching**: uses `unicodedata.normalize('NFD')` so "reforma" matches "Reforma" and "reformá".
- **Output schema** (8 fields): `titulo, cuerpo, bajada, fecha, fuente, url, fecha_scraping, query`
- `requirements.txt` uses `>=` version ranges (not pinned) because `pyarrow==16.1.0` has no pre-built wheel for Python 3.13.
- `run.py` log path uses `Path(__file__).parent` so it works regardless of working directory.
