import csv
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "datos"

SCHEMA = ["titulo", "cuerpo", "bajada", "fecha", "fuente", "url", "fecha_scraping", "query"]


def _query_slug(q: str) -> str:
    return re.sub(r"[^\w]+", "-", q.lower().strip()).strip("-")


def save_articles(
    articles: list[dict],
    slug: str,
    queries: Optional[list[str]] = None,
) -> Optional[Path]:
    if not articles:
        logger.info(f"[{slug}] no articles to save")
        return None

    outlet_dir = OUTPUT_DIR / slug
    outlet_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    query_part = "_".join(_query_slug(q) for q in queries if q.strip()) if queries else ""
    stem = f"{slug}_{query_part}_{timestamp}" if query_part else f"{slug}_{timestamp}"
    base = outlet_dir / stem

    _write_csv(articles, base.with_suffix(".csv"))
    _write_parquet(articles, base.with_suffix(".parquet"))

    logger.info(
        f"[{slug}] saved {len(articles)} articles -> {base}.csv / .parquet",
        extra={"tag": "EXPORT"},
    )
    return base


def _flatten(v) -> str:
    return re.sub(r"[\r\n]+", " ", str(v)) if isinstance(v, str) else v


def _write_csv(articles: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SCHEMA, extrasaction="ignore")
        writer.writeheader()
        for row in articles:
            writer.writerow({k: _flatten(v) for k, v in row.items()})


def _write_parquet(articles: list[dict], path: Path) -> None:
    rows = {col: [a.get(col, "") or "" for a in articles] for col in SCHEMA}
    table = pa.table({col: pa.array(rows[col], type=pa.string()) for col in SCHEMA})
    pq.write_table(table, path)
