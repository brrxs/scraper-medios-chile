"""
Schema conformance checker — reads all CSVs in datos/ and reports issues.
"""
import csv
import re
import sys
from pathlib import Path

DATOS_DIR = Path(__file__).parent / "datos"
SCHEMA = ["titulo", "cuerpo", "bajada", "fecha", "fuente", "url", "fecha_scraping", "query"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def check_outlet(slug: str, files: list[Path]) -> dict:
    total = ok = missing_date = short_body = short_title = 0
    for f in files:
        with open(f, encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        for row in rows:
            total += 1
            missing_cols = [c for c in SCHEMA if c not in row]
            if missing_cols:
                print(f"  [{slug}] missing columns in {f.name}: {missing_cols}")
                continue
            fecha = row.get("fecha", "")
            if not fecha or not DATE_RE.match(fecha):
                missing_date += 1
            if len(row.get("titulo", "")) < 20:
                short_title += 1
            if len(row.get("cuerpo", "")) < 400:
                short_body += 1
            else:
                ok += 1
    return {"total": total, "ok": ok, "missing_date": missing_date,
            "short_body": short_body, "short_title": short_title}


def main():
    if not DATOS_DIR.exists():
        print("datos/ directory not found.")
        sys.exit(1)

    outlet_dirs = [d for d in DATOS_DIR.iterdir() if d.is_dir()]
    if not outlet_dirs:
        print("No data found in datos/. Run: python run.py run --days 7")
        sys.exit(0)

    print(f"\n{'Outlet':<20} {'Total':>6} {'OK':>6} {'NoDate':>8} {'ShortBody':>10} {'ShortTitle':>11}")
    print("-" * 65)
    grand = {"total": 0, "ok": 0, "missing_date": 0, "short_body": 0, "short_title": 0}

    for d in sorted(outlet_dirs):
        csvs = list(d.glob("*.csv"))
        if not csvs:
            continue
        stats = check_outlet(d.name, csvs)
        for k in grand:
            grand[k] += stats[k]
        print(f"{d.name:<20} {stats['total']:>6} {stats['ok']:>6} {stats['missing_date']:>8} {stats['short_body']:>10} {stats['short_title']:>11}")

    print("-" * 65)
    print(f"{'TOTAL':<20} {grand['total']:>6} {grand['ok']:>6} {grand['missing_date']:>8} {grand['short_body']:>10} {grand['short_title']:>11}")
    print()
    if grand["total"] == 0:
        print("No articles found.")
    else:
        pct = round(100 * grand["ok"] / grand["total"])
        print(f"Pass rate: {pct}%  ({grand['ok']}/{grand['total']} articles meet all schema requirements)")


if __name__ == "__main__":
    main()
