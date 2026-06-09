# Plan: robots.txt compliance for the scraper

## Context

PressCL scrapes 16 Chilean news outlets. As part of the "ethical usage" work
(branch `ethical-update`, alongside the responsible-use disclaimer and hourly run
limit already shipped in `[0.4.1]`), the scraper should **respect each site's
robots.txt** before requesting a URL. A manual audit showed most outlets allow
general crawling; a few (notably emol.com) disallow news paths. The scraper must
honor those rules automatically and per-host.

Key facts established during exploration:
- HTML scraping goes through **two choke points** (the only ones robots.txt applies to):
  - `BaseScraper._fetch(url)` — `PressCL/app/scraper/base.py:236` (HTML)
  - `BasePlaywrightScraper._pw_get(url)` — `PressCL/app/scraper/base_playwright.py:30` (rendered HTML; overrides `_fetch`)
- **API scrapers are intentionally exempt** (per user decision). `BaseApiScraper._get`
  (`PressCL/app/scraper/base_api.py:114`) consumes explicit JSON data endpoints
  (e.g. emol via `newsapi.ecn.cl`, biobio via its `/api/buscador`), which are not
  web-crawling targets governed by robots.txt. **No robots check is added there.**
- Python stdlib `urllib.robotparser.RobotFileParser` covers parsing + `can_fetch`.
  **No new dependency.**
- Scrapers run in parallel threads (`ThreadPoolExecutor` in `app.py`), so the
  robots cache must be thread-safe.

Decisions confirmed with the user:
- **Disallowed URL → skip that URL and keep going** (log it; don't abort the outlet).
- **Crawl-delay → not honored**; keep the existing `DELAY_MIN/DELAY_MAX` delays.
- **robots.txt unreachable → fail-open** (allow scraping; a 404 already means allow-all).
- **API scrapers are exempt** — robots logic applies only to HTML scraping.

---

## New module: `PressCL/app/scraper/robots.py`

A small, self-contained, thread-safe robots checker.

- Module constant `BOT_UA = "prensa_chile_py"` — the user-agent token matched
  against robots groups (most sites only have `User-agent: *`, so this is mainly
  an identity label). Keep it consistent regardless of the heavier UA strings the
  HTTP/Playwright layers send.
- Module-level `_cache: dict[str, RobotFileParser | None]` keyed by host root
  (e.g. `https://www.emol.com`), guarded by a `threading.Lock`. Populated once per
  host per process.
- `_robots_for(host_root)`:
  - Fetch `host_root + "/robots.txt"` via `requests.get(..., timeout=10,
    headers={"User-Agent": BOT_UA})`.
  - On HTTP 200: `rp.parse(resp.text.splitlines())`.
  - On any non-200 (404, 403, etc.): leave the parser empty → `can_fetch` returns
    True (allow-all). This honors the **fail-open** decision and the "404 = allow"
    convention.
  - On `requests.RequestException`: cache `None` as a fail-open marker.
- `can_fetch(url: str) -> bool`:
  - Parse scheme+host with `urllib.parse.urlsplit`; if missing, return True.
  - Look up / build the parser for the host root.
  - If parser is `None` (fetch error), return True (fail-open).
  - Otherwise return `rp.can_fetch(BOT_UA, url)`.

> Note: Per RFC, 401/403 technically means "disallow all", but the user chose
> fail-open on errors, so we treat all non-200 responses as allow-all for
> simplicity. Document this briefly in a comment.

---

## Wire into the two HTML choke points

In each method, add the check at the very top and return `None` (the existing
"nothing fetched" signal that all callers already handle) when disallowed:

```python
if not robots.can_fetch(url):
    logger.info(f"[{self.SOURCE_SLUG}] robots.txt disallows {url}, skipping")
    return None
```

1. **`BaseScraper._fetch`** (`PressCL/app/scraper/base.py:236`) — `url`
   is already the full URL (search/index pages include query+page). Add
   `from scraper import robots` near `PressCL/app/scraper/base.py:13`.
   - Returning `None` for a disallowed *listing* page cleanly breaks pagination;
     for a disallowed *article* it's skipped. Both are the desired behavior.
2. **`BasePlaywrightScraper._pw_get`** (`PressCL/app/scraper/base_playwright.py:30`) —
   add the same guard at the top (Playwright overrides `_fetch`, so the base check
   doesn't run for it). Add `from scraper import robots`.

**`BaseApiScraper._get` is left untouched** — API scrapers are exempt (see Context).

No changes to delays (crawl-delay not honored, per decision).

---

## Optional: re-add a robots mention to the disclaimer

The disclaimer in `PressCL/app/app.py` previously referenced `robots.txt`
and the line was removed. Now that the tool actually complies, optionally restore a
softened bullet (e.g. "La herramienta respeta el archivo `robots.txt` de cada
medio"). Left optional — confirm before adding.

---

## Critical files

| File | Change |
|------|--------|
| `PressCL/app/scraper/robots.py` | **New** — thread-safe per-host robots checker over `urllib.robotparser` |
| `PressCL/app/scraper/base.py` | Import `robots`; guard in `_fetch` |
| `PressCL/app/scraper/base_playwright.py` | Import `robots`; guard in `_pw_get` |
| _(unchanged)_ `base_api.py` | API scrapers intentionally exempt — no robots check |
| `PressCL/CHANGELOG.md` | Add a `### Added` bullet under the unreleased `[0.4.1]` entry |

No new dependencies; `urllib.robotparser` and `requests` are already available.

---

## Verification

1. **Module sanity check** — quick REPL/script:
   ```python
   from scraper import robots
   # an HTML host that disallows a news path returns False:
   assert robots.can_fetch("https://www.emol.com/noticias/detalle/detalle_diario.asp") is False
   # an outlet with empty disallow:
   assert robots.can_fetch("https://elsiglo.cl/some-article/") is True
   ```
   Run from `PressCL/app/` so `scraper` is importable.
2. **End-to-end** — `streamlit run app/app.py`, accept the disclaimer, run a search
   over a small selection. Include **emol** and **biobio** (API-based, exempt) to
   confirm they are unaffected, plus one HTML outlet to confirm robots checks run.
3. **Disallow path is exercised** — temporarily point a scraper (or the REPL test) at
   a disallowed URL and confirm the log line `robots.txt disallows … skipping`
   appears and the URL is skipped rather than fetched.
4. **Fail-open** — confirm that a host with no robots.txt (404) or an unreachable
   robots.txt still scrapes normally (no exceptions, articles returned).
5. **No regression** — overall article counts for the allowed outlets are unchanged
   versus a pre-change run.
