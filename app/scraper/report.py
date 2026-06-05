"""Auto-report generator — called after every `run` command."""
import csv
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MIN_BODY = 400
_LOW_YIELD_THRESHOLD = 3

_OUTLET_TYPE = {
    "emol": "JSON API",
    "biobio": "JSON API",
    "t13": "Playwright",
    "24horas": "Playwright",
    "chvnoticias": "Playwright",
    "google_news": "RSS",
}


def _outlet_type(slug: str) -> str:
    return _OUTLET_TYPE.get(slug, "HTML")


def _scan_outlet_csvs(slug: str, datos_dir: Path) -> dict:
    """Read all CSVs for an outlet written in the most recent run (last 60 s)."""
    outlet_dir = datos_dir / slug
    if not outlet_dir.exists():
        return {"total": 0, "no_date": 0, "short_body": 0}

    # Pick the most recent timestamp batch
    csvs = sorted(outlet_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not csvs:
        return {"total": 0, "no_date": 0, "short_body": 0}

    newest_mtime = csvs[0].stat().st_mtime
    # Include all CSVs written within 60 s of the newest (same run)
    run_csvs = [c for c in csvs if newest_mtime - c.stat().st_mtime < 60]

    total = no_date = short_body = 0
    date_counts: dict[str, int] = {}
    for csv_path in run_csvs:
        try:
            with open(csv_path, encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    total += 1
                    fecha = row.get("fecha", "")
                    if not fecha or not _DATE_RE.match(fecha):
                        no_date += 1
                    if len(row.get("cuerpo", "")) < _MIN_BODY:
                        short_body += 1
                    if slug == "google_news" and fecha:
                        date_counts[fecha] = date_counts.get(fecha, 0) + 1
        except Exception:
            pass

    cap_days = sorted(d for d, c in date_counts.items() if c >= 100) if slug == "google_news" else []
    return {"total": total, "no_date": no_date, "short_body": short_body, "cap_days": cap_days}


def write_run_report(
    results: list[tuple[str, int, Optional[str]]],
    since: date,
    until: date,
    queries,
    datos_dir: Path,
    reports_dir: Path,
    interrupted: bool = False,
) -> Path:
    """`queries` may be: None, a single str (legacy), or a list[str] (multi-query)."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"report_{timestamp}.md"

    if queries is None:
        query_str = "(none)"
    elif isinstance(queries, str):
        query_str = queries
    else:
        query_str = ", ".join(queries) if queries else "(none)"

    lines: list[str] = []

    # --- Header ---
    title = "# Scraping Run Report (INTERRUPTED — partial results)" if interrupted else "# Scraping Run Report"
    lines += [
        title,
        f"",
        f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Query:** `{query_str}`  ",
        f"**Window:** {since} to {until}  ",
    ]
    if interrupted:
        not_run = [s for s, _, e in results if e == "NOT RUN"]
        lines.append(
            f"**Status:** Run was interrupted. "
            f"{len(results) - len(not_run)}/{len(results)} outlets completed. "
            f"Missing: {', '.join(f'`{s}`' for s in not_run) if not_run else 'none'}  "
        )
    lines.append("")

    # --- Results table ---
    ok_results = [(s, n) for s, n, e in results if e is None]
    failed_results = [(s, e) for s, n, e in results if e is not None and e != "NOT RUN"]
    not_run_results = [(s, e) for s, n, e in results if e == "NOT RUN"]
    total_articles = sum(n for _, n in ok_results)

    stats_by_slug: dict[str, dict] = {}
    for slug, n, err in results:
        if err is None:
            stats_by_slug[slug] = _scan_outlet_csvs(slug, datos_dir)
        else:
            stats_by_slug[slug] = {"total": 0, "no_date": 0, "short_body": 0}

    lines += [
        f"## Results",
        f"",
        f"| Outlet | Type | Articles | NoDate | ShortBody | Status |",
        f"|---|---|---|---|---|---|",
    ]
    for slug, n, err in sorted(results, key=lambda x: x[0]):
        s = stats_by_slug[slug]
        if err is None:
            status = "OK"
        elif err == "NOT RUN":
            status = "NOT RUN"
        else:
            status = "FAILED"
        lines.append(
            f"| `{slug}` | {_outlet_type(slug)} | {s['total']} "
            f"| {s['no_date']} | {s['short_body']} | {status} |"
        )

    lines += [
        f"",
        f"**Total articles:** {total_articles}  ",
        f"**Outlets OK:** {len(ok_results)} / {len(results)}  ",
        f"",
    ]

    # --- Flags ---
    flags: list[str] = []

    for slug, n, err in results:
        s = stats_by_slug[slug]
        if err == "NOT RUN":
            continue
        if err is not None:
            flags.append(
                f"- **`{slug}` FAILED** — `{err[:120]}`  \n"
                f"  Check the logs for the full traceback."
            )
        if s["no_date"] > 0:
            pct = int(100 * s["no_date"] / s["total"]) if s["total"] else 0
            flags.append(
                f"- **`{slug}` — {s['no_date']}/{s['total']} articles missing date ({pct}%)**  \n"
                f"  The date selector may not cover all article layouts. "
                f"  Consider adding a `<meta property=\"article:published_time\">` fallback."
            )
        if s["short_body"] > 0 and slug != "google_news":
            flags.append(
                f"- **`{slug}` — {s['short_body']} articles with short body (<{_MIN_BODY} chars)**  \n"
                f"  The `body_selector` may be broken or the site's layout changed."
            )
        if slug == "google_news" and s.get("cap_days"):
            days_str = ", ".join(f"`{d}`" for d in s["cap_days"])
            flags.append(
                f"- **`google_news` — RSS cap (100 results/day) reached on: {days_str}**  \n"
                f"  Results for these days may be incomplete. "
                f"  Add more `--query` phrases to increase coverage "
                f"  (each phrase gets its own 100-result slot per day)."
            )
        if err is None and s["total"] == 0:
            flags.append(
                f"- **`{slug}` — 0 articles collected**  \n"
                f"  Possible causes: query not found, site blocked the scraper, or selector rot. "
                f"  Run `python run.py check {slug}` to verify."
            )

    low_yield = [
        slug for slug, n, err in results
        if err is None and 0 < stats_by_slug[slug]["total"] < _LOW_YIELD_THRESHOLD
    ]

    if flags or low_yield:
        lines += ["## Flags", ""]
        if flags:
            lines += flags + [""]
        if low_yield:
            slugs_str = ", ".join(f"`{s}`" for s in sorted(low_yield))
            lines += [
                f"### Low-yield outlets",
                f"",
                f"The following outlets returned fewer than {_LOW_YIELD_THRESHOLD} articles "
                f"for this query/window: {slugs_str}  ",
                f"This is not necessarily a bug — it may reflect low coverage of the query topic.",
                f"",
            ]
    else:
        lines += ["## Flags", "", "No issues detected.", ""]

    # --- Failed outlets ---
    if failed_results:
        lines += ["## Errors", ""]
        for slug, err in failed_results:
            lines += [f"### `{slug}`", f"```", err, f"```", ""]

    # --- Not-run outlets (interrupted run) ---
    if not_run_results:
        slugs_str = ", ".join(f"`{s}`" for s, _ in not_run_results)
        lines += [
            "## Not run (interrupted)",
            "",
            f"The following outlets did not execute because the run was stopped: {slugs_str}  ",
            f"Re-run with the same query targeting only these outlets to collect missing data:",
            f"",
            f"```powershell",
            f"python run.py run {' '.join(s for s, _ in not_run_results)} --query \"...\" --since {since} --to {until}",
            f"```",
            "",
        ]

    # --- Footer ---
    lines += [
        "---",
        f"*Data saved to: `datos/`*  ",
        f"*Report generated by prensa_chile_py*",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    import logging
    logging.getLogger(__name__).info(f"Report written -> {report_path}")
    return report_path
