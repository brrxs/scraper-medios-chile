import argparse
import logging
import logging.handlers
import multiprocessing
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from scraper.outlets import REGISTRY

_LOG_FILE = Path(__file__).parent / "logs" / "scraping.log"
_DATOS_DIR = Path(__file__).parent / "datos"
_CURATED_DIR = Path(__file__).parent / "datos" / "curated"
_REPORTS_DIR = Path(__file__).parent / "reports"

_TAG_COLORS: dict[str, str] = {
    "INIT":    "\033[36m",    # cyan
    "EXPORT":  "\033[32m",    # green
    "DONE":    "\033[1;32m",  # bold green
    "WARNING": "\033[33m",    # yellow
    "ERROR":   "\033[31m",    # red
}
_RESET = "\033[0m"


class _LevelTagFormatter(logging.Formatter):
    def __init__(self, *args, use_color: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        tag = getattr(record, "tag", None)
        if tag:
            saved, record.levelname = record.levelname, tag
            result = super().format(record)
            record.levelname = saved
        else:
            tag = record.levelname
            result = super().format(record)
        if self.use_color:
            color = _TAG_COLORS.get(tag, "")
            if color:
                result = result.replace(f"[{tag}]", f"{color}[{tag}]{_RESET}", 1)
        return result


_fmt_plain = _LevelTagFormatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S", use_color=False)
_fmt_color = _LevelTagFormatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S", use_color=True)
_sh = logging.StreamHandler(sys.stdout)
_sh.setFormatter(_fmt_color)
_fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
_fh.setFormatter(_fmt_plain)
_root = logging.getLogger()
_root.setLevel(logging.INFO)
_root.handlers.clear()
_root.addHandler(_sh)
_root.addHandler(_fh)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Worker — runs in a subprocess (must be module-level for Windows spawn)
# ---------------------------------------------------------------------------

def _run_outlet(args: tuple) -> tuple[str, int, Optional[str]]:
    slug, queries, since, until, log_queue = args
    if multiprocessing.current_process().name != "MainProcess":
        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(logging.handlers.QueueHandler(log_queue))
        root.setLevel(logging.INFO)
    from scraper.outlets import REGISTRY as _REG
    try:
        scraper = _REG[slug]()
        articles = scraper.run(queries=queries, since=since, until=until)
        return (slug, len(articles) if articles else 0, None)
    except Exception as e:
        return (slug, 0, str(e))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scraper de prensa chilena — Monitor Social UC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python run.py run                                          # all outlets, last 7 days
  python run.py run --query "pobreza vivienda"               # search all outlets
  python run.py run --query "pobreza" --since 2025-05-01     # from date
  python run.py run --query "pobreza" --since 2025-05-01 --to 2025-05-15
  python run.py run --query "pobreza" --days 14              # last N days
  python run.py run elsiglo emol --query "trabajo" --days 30
  python run.py run --workers 6 --progress                   # parallel + live table
  python run.py merge --query "Mara Sedini" --since 2026-03-11
  python run.py list
  python run.py check elmostrador
""",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = subparsers.add_parser("run", help="Run scrapers")
    p_run.add_argument("outlets", nargs="*", help="Outlet slugs (omit for all)")
    p_run.add_argument(
        "--query", "-q", action="append", default=None,
        help="Search phrase (AND within, OR across). Repeat for parallel phrases, "
             "e.g. --query \"Mara Sedini\" --query \"Sedini\".",
    )
    p_run.add_argument("--since", default=None, help="Start date YYYY-MM-DD (inclusive)")
    p_run.add_argument("--to", default=None, dest="until", help="End date YYYY-MM-DD (inclusive)")
    p_run.add_argument("--days", type=int, default=None, help="Last N days (overrides --since/--to)")
    p_run.add_argument("--workers", "-w", type=int, default=None,
                       help="Parallel worker processes (default: min(outlets, 4))")
    p_run.add_argument("--progress", action="store_true",
                       help="Show a live rich progress table during scraping")
    p_run.add_argument("--gn-full", action="store_true", dest="gn_full",
                       help="Google News: fetch full article text via Playwright "
                            "(slower; default is RSS snippet only)")

    # list
    subparsers.add_parser("list", help="List available outlets")

    # merge
    p_merge = subparsers.add_parser("merge", help="Merge scraped articles into a single curated dataset")
    p_merge.add_argument(
        "--query", "-q", action="append", default=None,
        help="Filter phrase (AND within, OR across). Repeat for parallel phrases.",
    )
    p_merge.add_argument("--since", default=None, help="Keep articles on or after YYYY-MM-DD")
    p_merge.add_argument("--to", default=None, dest="until", help="Keep articles on or before YYYY-MM-DD")

    # clean
    p_clean = subparsers.add_parser(
        "clean", help="Delete raw outlet files and/or reports"
    )
    p_clean.add_argument(
        "outlets", nargs="*",
        help="Outlet slugs to clean (omit for all). Ignored with --reports-only.",
    )
    p_clean.add_argument(
        "--reports", action="store_true",
        help="Also delete all files in reports/",
    )
    p_clean.add_argument(
        "--reports-only", action="store_true", dest="reports_only",
        help="Delete only report files; leave datos/ untouched",
    )
    p_clean.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="List files that would be deleted without removing them",
    )

    # check
    p_check = subparsers.add_parser("check", help="Verify selectors for an outlet (no data saved)")
    p_check.add_argument("outlet", choices=list(REGISTRY))

    args = parser.parse_args()

    if args.command == "list":
        print("\nAvailable outlets:")
        for slug in sorted(REGISTRY):
            print(f"  {slug}")
        print()

    elif args.command == "run":
        _cmd_run(args)

    elif args.command == "merge":
        _cmd_merge(args)

    elif args.command == "clean":
        _cmd_clean(args)

    elif args.command == "check":
        _check(args.outlet)


def _cmd_run(args):
    if getattr(args, "gn_full", False):
        os.environ["GNEWS_FULLTEXT"] = "1"
    since, until = _resolve_dates(args)
    targets = args.outlets if args.outlets else list(REGISTRY)
    invalid = [s for s in targets if s not in REGISTRY]
    if invalid:
        print(f"Unknown outlet(s): {', '.join(invalid)}. Run 'python run.py list'.")
        sys.exit(1)

    n_workers = args.workers if args.workers is not None else min(len(targets), 4)
    use_progress = args.progress

    logger.info(
        f"Running {len(targets)} outlet(s) | since={since} until={until} "
        f"query={args.query!r} | workers={n_workers}"
    )

    # Set up logging queue so subprocesses send records to the main process.
    # Must use Manager().Queue() on Windows (spawn) — plain Queue() is not picklable
    # when passed as an argument through pool.map.
    manager = multiprocessing.Manager()
    log_queue = manager.Queue()
    listener = logging.handlers.QueueListener(
        log_queue, *logging.getLogger().handlers, respect_handler_level=True
    )
    listener.start()

    worker_args = [(s, args.query, since, until, log_queue) for s in targets]
    results: list[tuple[str, int, Optional[str]]] = []
    interrupted = False
    t0 = time.monotonic()

    try:
        if use_progress:
            _run_with_progress(worker_args, targets, n_workers, log_queue, results)
        elif n_workers == 1:
            for wa in worker_args:
                results.append(_run_outlet(wa))
        else:
            with multiprocessing.Pool(processes=n_workers) as pool:
                for result in pool.imap_unordered(_run_outlet, worker_args):
                    results.append(result)
    except KeyboardInterrupt:
        interrupted = True
        logger.warning(
            "Run interrupted — partial results for %d/%d outlets.", len(results), len(targets)
        )
    except Exception as e:
        logger.error(f"Pool error: {e}", exc_info=True)
    finally:
        # Mark outlets that never completed
        completed = {s for s, _, _ in results}
        for slug in targets:
            if slug not in completed:
                results.append((slug, 0, "NOT RUN"))

        elapsed = time.monotonic() - t0
        _log_summary(results, elapsed)

        from scraper.report import write_run_report
        write_run_report(
            results, since, until, args.query, _DATOS_DIR, _REPORTS_DIR, interrupted=interrupted
        )

        listener.stop()
        manager.shutdown()


def _run_with_progress(
    worker_args: list,
    targets: list[str],
    n_workers: int,
    log_queue: multiprocessing.Queue,
    results: list,
) -> None:
    try:
        from rich.live import Live
        from rich.table import Table
        from rich.console import Console
    except ImportError:
        logger.warning("rich not installed — falling back to plain logging. Run: pip install rich")
        if n_workers == 1:
            for wa in worker_args:
                results.append(_run_outlet(wa))
        else:
            with multiprocessing.Pool(processes=n_workers) as pool:
                for result in pool.imap_unordered(_run_outlet, worker_args):
                    results.append(result)
        return

    console = Console()
    status: dict[str, dict] = {
        slug: {"status": "Pending", "articles": "-", "elapsed": "-", "start": None}
        for slug in targets
    }

    def make_table() -> Table:
        table = Table(title="Scraping Progress", show_lines=False)
        table.add_column("Outlet", style="cyan", width=18)
        table.add_column("Status", width=22)
        table.add_column("Articles", justify="right", width=10)
        table.add_column("Elapsed", justify="right", width=10)
        for slug in targets:
            s = status[slug]
            elapsed_str = s["elapsed"]
            if s["start"] is not None and elapsed_str == "-":
                elapsed_str = f"{time.monotonic() - s['start']:.0f}s"
            table.add_row(slug, s["status"], str(s["articles"]), elapsed_str)
        return table

    def drain_queue():
        root = logging.getLogger()
        while not log_queue.empty():
            try:
                record = log_queue.get_nowait()
                root.handle(record)
                msg = record.getMessage()
                for slug in targets:
                    if f"[{slug}]" not in msg:
                        continue
                    if status[slug]["start"] is None:
                        status[slug]["start"] = time.monotonic()
                    if "scraping" in msg and "URLs" in msg:
                        status[slug]["status"] = "Scraping..."
                    elif "articles collected" in msg:
                        n = msg.split()[msg.split().index("articles") - 1]
                        status[slug]["articles"] = n
                        status[slug]["status"] = "Done"
                        if status[slug]["start"]:
                            status[slug]["elapsed"] = f"{time.monotonic() - status[slug]['start']:.0f}s"
                    elif "search empty" in msg or "falling back" in msg:
                        status[slug]["status"] = "Collecting..."
                    elif "FAILED" in msg or "error" in msg.lower():
                        status[slug]["status"] = "[red]Error[/red]"
            except Exception:
                pass

    with Live(make_table(), console=console, refresh_per_second=2) as live:
        if n_workers == 1:
            for wa in worker_args:
                slug = wa[0]
                status[slug]["status"] = "Running..."
                status[slug]["start"] = time.monotonic()
                live.update(make_table())
                res = _run_outlet(wa)
                results.append(res)
                _, n, err = res
                status[slug]["status"] = "Done" if err is None else "[red]FAILED[/red]"
                status[slug]["articles"] = str(n)
                status[slug]["elapsed"] = f"{time.monotonic() - status[slug]['start']:.0f}s"
                live.update(make_table())
        else:
            with multiprocessing.Pool(processes=n_workers) as pool:
                # apply_async per outlet so results are collected as each one finishes
                pending = {wa[0]: pool.apply_async(_run_outlet, (wa,)) for wa in worker_args}
                collected: set[str] = set()

                while len(collected) < len(pending):
                    drain_queue()
                    for slug, ar in list(pending.items()):
                        if slug in collected or not ar.ready():
                            continue
                        try:
                            res = ar.get()
                        except Exception as e:
                            res = (slug, 0, str(e))
                        results.append(res)
                        collected.add(slug)
                        _, n, err = res
                        status[slug]["status"] = "Done" if err is None else "[red]FAILED[/red]"
                        status[slug]["articles"] = str(n)
                        if status[slug]["start"]:
                            status[slug]["elapsed"] = f"{time.monotonic() - status[slug]['start']:.0f}s"
                    live.update(make_table())
                    if len(collected) < len(pending):
                        time.sleep(0.5)
                drain_queue()
                live.update(make_table())


def _log_summary(results: list, elapsed: float):
    ok = [(s, n) for s, n, e in results if e is None]
    failed = [(s, e) for s, n, e in results if e is not None]
    logger.info(
        f"=== Run complete in {elapsed:.0f}s: {len(ok)} OK, {len(failed)} failed ===",
        extra={"tag": "DONE"},
    )
    for slug, n in sorted(ok):
        logger.info(f"  {slug}: {n} articles")
    for slug, err in failed:
        logger.error(f"  {slug}: FAILED — {err}")


def _cmd_clean(args):
    files: list[Path] = []

    if not args.reports_only:
        if args.outlets:
            slugs = args.outlets
        else:
            slugs = [
                d.name for d in sorted(_DATOS_DIR.iterdir())
                if d.is_dir() and d.name != "curated"
            ]
        for slug in slugs:
            outlet_dir = _DATOS_DIR / slug
            if not outlet_dir.is_dir():
                print(f"  Warning: datos/{slug}/ not found, skipping.")
                continue
            for f in sorted(outlet_dir.iterdir()):
                if f.suffix in (".csv", ".parquet"):
                    files.append(f)

    if args.reports or args.reports_only:
        for f in sorted(_REPORTS_DIR.glob("*.md")):
            files.append(f)

    if not files:
        print("No files found to delete.")
        return

    label = "[dry-run] Would delete" if args.dry_run else "Will delete"
    print(f"\n{label} {len(files)} file(s):")
    for f in files:
        print(f"  {f}")

    if args.dry_run:
        print("\n[dry-run] No files deleted.")
        return

    for f in files:
        f.unlink()
    print(f"\nDeleted {len(files)} file(s).")
    logger.info(f"clean: removed {len(files)} file(s)")


def _cmd_merge(args):
    import csv
    import re
    import unicodedata
    import pyarrow as pa
    import pyarrow.parquet as pq
    from scraper.output import SCHEMA
    from scraper.utils import any_phrase_matches

    def _slugify(text: str) -> str:
        text = unicodedata.normalize("NFD", text.lower())
        text = "".join(c for c in text if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+", "-", text).strip("-")

    _GN_PREFIX = re.compile(r'^\[([^\]]+)\]\s*')
    _GN_SUFFIX = re.compile(r'\s*-\s*[^-]+\|?\s*$')

    def _normalize_gn(row: dict) -> dict:
        if row.get("fuente") != "google_news":
            return row
        # cuerpo has the prefix for legacy RSS-only rows; bajada has it for enriched rows
        for field in ("cuerpo", "bajada"):
            m = _GN_PREFIX.match(row.get(field) or "")
            if m:
                row["fuente"] = m.group(1).rstrip(" |").strip()
                break
        row["titulo"] = _GN_SUFFIX.sub("", row.get("titulo") or "").strip()
        # Preserve full-text cuerpo; only clear it if it's still the short RSS snippet
        if not row.get("cuerpo") or _GN_PREFIX.match(row.get("cuerpo") or ""):
            row["cuerpo"] = ""
        row["bajada"] = ""
        return row

    # Parse date filters
    since = date.fromisoformat(args.since) if args.since else None
    until = date.fromisoformat(args.until) if args.until else None
    query_phrases: list[str] = [q for q in (args.query or []) if q and q.strip()]

    # Scan all outlet CSVs (skip curated/)
    seen_urls: set[str] = set()
    rows: list[dict] = []
    for csv_path in sorted(_DATOS_DIR.glob("*/*.csv")):
        if "curated" in csv_path.parts:
            continue
        try:
            with open(csv_path, encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    url = row.get("url", "")
                    if url in seen_urls:
                        continue
                    # Date filter
                    fecha = row.get("fecha", "")
                    if fecha:
                        try:
                            d = date.fromisoformat(fecha)
                            if since and d < since:
                                continue
                            if until and d > until:
                                continue
                        except ValueError:
                            pass
                    # Query filter — AND within phrase, OR across phrases.
                    if query_phrases:
                        haystack = (row.get("titulo") or "") + " " + (row.get("cuerpo") or "")
                        if not any_phrase_matches(haystack, query_phrases):
                            continue
                    seen_urls.add(url)
                    rows.append(_normalize_gn(row))
        except Exception as e:
            logger.warning(f"Could not read {csv_path}: {e}")

    if not rows:
        print("No articles matched the given filters.")
        return

    # Sort by date then source
    rows.sort(key=lambda r: (r.get("fecha") or "", r.get("fuente") or ""))

    # Build output filename
    today_str = date.today().strftime("%Y%m%d")
    query_slug = "-".join(_slugify(q) for q in query_phrases) if query_phrases else "all"
    since_str = f"-desde-{args.since.replace('-', '')}" if args.since else ""
    stem = f"{query_slug}-dataset{since_str}-{today_str}"

    _CURATED_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = _CURATED_DIR / f"{stem}.csv"
    parquet_path = _CURATED_DIR / f"{stem}.parquet"

    def _flatten(v):
        return re.sub(r"[\r\n]+", " ", str(v)) if isinstance(v, str) else v

    # Write CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SCHEMA, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _flatten(v) for k, v in row.items()})

    # Write Parquet
    data = {col: [r.get(col, "") or "" for r in rows] for col in SCHEMA}
    table = pa.table({col: pa.array(data[col], type=pa.string()) for col in SCHEMA})
    pq.write_table(table, parquet_path)

    # Summary
    sources = {}
    for r in rows:
        sources[r.get("fuente", "?")] = sources.get(r.get("fuente", "?"), 0) + 1
    print(f"\nMerged {len(rows)} articles -> {csv_path.name}")
    print(f"  Location: {_CURATED_DIR}")
    print(f"  Outlets:  {len(sources)}")
    for src, n in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"    {src:<20} {n} articles")
    logger.info(f"Merged dataset written -> {csv_path}")


def _resolve_dates(args) -> tuple[date, date]:
    today = date.today()
    if args.days is not None:
        return today - timedelta(days=args.days), today
    since = date.fromisoformat(args.since) if args.since else today - timedelta(days=7)
    until = date.fromisoformat(args.until) if args.until else today
    return since, until


# ---------------------------------------------------------------------------
# check subcommand
# ---------------------------------------------------------------------------

def _check(slug: str):
    from scraper.base_api import BaseApiScraper
    from scraper.base_playwright import BasePlaywrightScraper

    scraper = REGISTRY[slug]()
    print(f"\n--- Checking: {slug} ---")

    if isinstance(scraper, BaseApiScraper):
        print("Type: JSON API scraper")
        # Some APIs return latest for empty q; others (biobio) require a term.
        # Try empty first, fall back to a generic Spanish term.
        for probe in ("", "chile"):
            print(f"Fetching first batch from API (offset=0, query={probe!r})...")
            batch = scraper._fetch_page(probe, 0)
            if batch:
                break
        if not batch:
            print("BROKEN — API returned empty or error response")
            return
        print(f"OK — API returned {len(batch)} items")
        first = batch[0]
        article = scraper._map_article(first)
        if article:
            print(f"  titulo:  {str(article.get('titulo', ''))[:70]}")
            print(f"  fecha:   {article.get('fecha')}")
            print(f"  cuerpo:  {len(article.get('cuerpo') or '')} chars")
        else:
            print("  WARN — first item failed _map_article validation")
        return

    if isinstance(scraper, BasePlaywrightScraper):
        _check_playwright(scraper)
        return

    _check_html(scraper)


def _check_html(scraper):
    import requests
    from bs4 import BeautifulSoup

    print("Type: HTML scraper")
    print(f"INDEX_URL:  {scraper.INDEX_URL_TEMPLATE.format(page=1)}")
    search_tmpl = scraper.SEARCH_URL_TEMPLATE
    print(f"SEARCH_URL: {search_tmpl.format(query='test', page=1) if search_tmpl else '(none)'}")
    print()

    index_url = scraper.INDEX_URL_TEMPLATE.format(page=1)
    try:
        resp = requests.get(index_url, headers=scraper.HEADERS, timeout=20)
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"BROKEN — could not fetch index page: {e}")
        return

    links = scraper._extract_links(soup)
    raw_elements = soup.select(scraper.link_selector)
    print(f"link_selector ({scraper.link_selector!r}): {len(raw_elements)} elements, {len(links)} valid URLs")
    if not links:
        print("  BROKEN — no article URLs found on index page")
        return

    first_url = links[0]
    print(f"First article URL: {first_url}")
    try:
        resp2 = requests.get(first_url, headers=scraper.HEADERS, timeout=20)
        soup2 = BeautifulSoup(resp2.text, "lxml")
    except Exception as e:
        print(f"BROKEN — could not fetch article: {e}")
        return

    _print_selector_results(scraper, soup2)
    article = scraper._scrape_article_safe(first_url)
    _print_article_result(article)


def _check_playwright(scraper):
    from playwright.sync_api import sync_playwright

    print("Type: Playwright scraper (headless Chromium)")
    print(f"INDEX_URL:  {scraper.INDEX_URL_TEMPLATE}")
    print()

    with sync_playwright() as pw:
        scraper._browser = pw.chromium.launch(headless=True)
        try:
            links = scraper._collect_urls_feed(None, None)
            print(f"link_selector ({scraper.link_selector!r}): {len(links)} valid URLs")
            if not links:
                print("  BROKEN — no article URLs found on index page")
                return

            first_url = links[0]
            print(f"First article URL: {first_url}")
            soup2 = scraper._fetch(first_url)
            if soup2 is None:
                print("BROKEN — could not fetch article page")
                return

            _print_selector_results(scraper, soup2)
            article = scraper._scrape_article_safe(first_url)
        finally:
            scraper._browser.close()
            scraper._browser = None

    _print_article_result(article)


def _print_selector_results(scraper, soup):
    for attr, selector in [
        ("title_selector",    scraper.title_selector),
        ("date_selector",     scraper.date_selector),
        ("body_selector",     scraper.body_selector),
        ("subtitle_selector", scraper.subtitle_selector),
    ]:
        if selector is None:
            print(f"  {attr}: None (skipped)")
            continue
        els = soup.select(selector)
        if els:
            preview = els[0].get_text(strip=True)[:80]
            print(f"  {attr} ({selector!r}): {len(els)} elements. First: '{preview}'")
        else:
            print(f"  {attr} ({selector!r}): BROKEN — 0 elements found")


def _print_article_result(article):
    print()
    if article:
        print("Article parsed OK:")
        print(f"  titulo:  {str(article.get('titulo', ''))[:70]}")
        print(f"  fecha:   {article.get('fecha')}")
        print(f"  cuerpo:  {len(article.get('cuerpo') or '')} chars")
    else:
        print("Article parse FAILED (title/body too short or selector mismatch)")


if __name__ == "__main__":
    main()
