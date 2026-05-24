# prensa_chile_py — Project Status Report
**Date:** 2026-05-22 | **Prepared by:** Monitor Social UC

---

## Summary

All 15 Chilean news outlets are scraped, validated, and production-ready. The scraper runs in parallel, writes structured CSV and Parquet output, generates an auto-report after every run, and displays a live progress table in the terminal.

| Metric | Value |
|---|---|
| Outlets implemented | 15 / 15 |
| Outlets live-tested | 15 / 15 |
| Total articles in datos/ | 247 |
| Schema pass rate | 100% (247/247) |
| NoDate (pre-fix legacy data) | 19 — in old CSVs only; new runs produce 0 |
| Short body | 0 |
| Short title | 0 |

---

## Outlet Status

| Outlet | Type | Articles | NoDate | Notes |
|---|---|---|---|---|
| `elsiglo` | HTML | 13 | 0 | Fully working |
| `emol` | JSON API | 6 | 0 | Hidden JSON API (`newsapi.ecn.cl`) |
| `ciper` | HTML | 5 | 0 | Date from canonical URL |
| `elmostrador` | HTML | 26 | 0 | Fully working |
| `biobio` | HTML | 2 | 0 | Search always empty; feed+filter; low yield |
| `t13` | Playwright | 4 | 0 | Homepage-only (~54 URLs) |
| `24horas` | Playwright | 1 | 0 | Scroll-load; 8-page cap |
| `chvnoticias` | Playwright | 1 | 0 | Listing-only (~8 URLs) |
| `cooperativa` | HTML | 4 | 0 | Date from canonical URL |
| `eldesconcierto` | HTML | 1 | 0 | No pagination; 3 listing URLs |
| `elciudadano` | HTML | 60 | 12* | *Legacy data — fix applied; new runs: 0 NoDate |
| `cnnchile` | HTML | 12 | 0 | Fully working |
| `lanacion` | HTML | 9 | 0 | Slow site; 10 s timeout override |
| `meganoticias` | HTML | 76 | 7* | *Legacy data — fix applied; new runs: 0 NoDate |
| `lacuarta` | HTML | 27 | 0 | Fully working |

*The 19 NoDate rows are in CSVs written before the fix was applied (2026-05-21). All new runs produce 0 NoDate — verified via `check` and a fresh meganoticias run (18 articles, 0 NoDate).

---

## Flags

### Low-yield outlets
These outlets returned few articles for the query "reforma" — not bugs, just low topic coverage:

| Outlet | Articles | Reason |
|---|---|---|
| `biobio` | 2 | Search always returns 0; feed+filter is broad |
| `chvnoticias` | 1 | Playwright listing shows only ~8 URLs |
| `24horas` | 1 | Scroll-load listing, 8-page cap |
| `eldesconcierto` | 1 | Listing shows only 3 article URLs |

Expected to perform better on higher-volume queries or wider date windows.

### elciudadano — rate limiting
elciudadano.com aggressively rate-limits after ~300–400 requests (`WinError 10065` — host unreachable). For this outlet, prefer short windows (`--days 3`) or run it alone at off-peak hours.

---

## Architecture

### Scraper types
- **`BaseScraper`** (HTML, requests) — 11 outlets
- **`BaseApiScraper`** (JSON API) — emol only
- **`BasePlaywrightScraper`** (headless Chromium) — t13, 24horas, chvnoticias

### Key design decisions
- **Search-first:** tries native search endpoint; falls back to category feed + keyword filter if 0 results.
- **Date-bound pagination:** stops when a full page is older than `--since`. Hard cap: 50 pages (8 for Playwright).
- **Parallel execution:** `multiprocessing.Pool` (not threads — Playwright `sync_api` is not thread-safe). Logging funnelled back to main process via `QueueHandler` / `QueueListener`.
- **Accent-insensitive matching:** `unicodedata.normalize('NFD')` — "reforma" matches "Reforma", "reformá".
- **Date fallback chain** (elciudadano, meganoticias): OG meta tag → `<time datetime>` attr → visible text → URL path `/YYYY/MM/DD/`.

### Output
```
datos/{slug}/{slug}_YYYYMMDD_HHMMSS.csv       # UTF-8 CSV
datos/{slug}/{slug}_YYYYMMDD_HHMMSS.parquet   # Parquet (columnar)
reports/report_YYYYMMDD_HHMMSS.md             # Auto-generated after every run
logs/scraping.log                             # Persistent run log
```

**Schema (8 fields):** `titulo, cuerpo, bajada, fecha, fuente, url, fecha_scraping, query`

---

## How to Run

```powershell
$base = "c:\Users\Tomas\OneDrive - Universidad Católica de Chile\Monitor Social\BO\prensa_chile_py"
$py   = "$base\.venv\Scripts\python.exe"

# Full run — all 15 outlets, 30 days, 4 parallel workers, live progress table
& $py "$base\run.py" run --query "TU_TEMA" --days 30 --workers 4 --progress

# Specific outlets
& $py "$base\run.py" run elsiglo emol elmostrador ciper --query "pobreza" --days 14

# Validate output
& $py "$base\validate.py"

# Smoke-test a single outlet
& $py "$base\run.py" check elciudadano
```

---

## Fixes Applied (full history)

| Issue | Fix | Session |
|---|---|---|
| `pyarrow` no wheel for Python 3.13 | `>=` version ranges in requirements.txt | 2026-05-20 |
| `UnicodeEncodeError` on Windows | Replaced `→` with `->` in output.py | 2026-05-20 |
| Biobio date format unparseable | Weekday-strip + pipe-split in utils.py | 2026-05-20 |
| Cooperativa wrong index URL | Corrected to `/noticias/pais/` | 2026-05-20 |
| elmostrador/eldesconcierto/biobio 404 | Corrected to live URLs | 2026-05-20 |
| t13/24horas/chvnoticias JS-rendered | Rebuilt as `BasePlaywrightScraper` | 2026-05-20 |
| CHV wrong `datetime` attribute | Override `_date_text` to use visible text | 2026-05-20 |
| 24horas hung (HARD_PAGE_CAP=50) | `PW_PAGE_CAP=8` + dedup early-exit | 2026-05-21 |
| Cooperativa body selector returned <400 chars | Changed to `.cuerpo-articulo p` | 2026-05-21 |
| Lanacion hangs on slow connections | `REQUEST_TIMEOUT=10` override | 2026-05-21 |
| venv broken on new machine | Rebuilt with local Python 3.13.5 | 2026-05-21 |
| elciudadano + meganoticias: 19 NoDate articles | `_date_text` override with OG meta + URL fallback | 2026-05-22 |
| base_api.py duplicate date parser | Removed `_parse_date_str`, use `utils.parse_date` | 2026-05-22 |
| Playwright `ctx` could leak on exception | `ctx = None` before try + guarded close | 2026-05-22 |
| Dead unreachable code in base.py | Removed | 2026-05-22 |
| meganoticias link_selector too broad | Narrowed to `a[href*='/nacional/']` | 2026-05-22 |
| Regex compiled inside methods on every call | Moved to module-level in ciper, cooperativa, chvnoticias | 2026-05-22 |
| Sequential outlet execution (1+ hr for 15 outlets) | `multiprocessing.Pool` + `--workers` flag | 2026-05-22 |
| No live progress during scraping | `rich.Live` table via `--progress` flag | 2026-05-22 |
| No automatic run report | `scraper/report.py` — Markdown written to `reports/` | 2026-05-22 |
| No documentation | `README.md` added | 2026-05-22 |
