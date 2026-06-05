"""Biobío Chile — JSON API scraper.

Uses the hidden search API at /lista/api/buscador (same endpoint the
`datamedios` R package uses). The public HTML search page is JS-rendered and
yields zero results to `requests`, so the API is the only viable path.
"""
import logging
from datetime import datetime
from html import unescape
from typing import Optional

from bs4 import BeautifulSoup

from scraper.base_api import BaseApiScraper

logger = logging.getLogger(__name__)

API_URL = "https://www.biobiochile.cl/lista/api/buscador"

API_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) "
        "Gecko/20100101 Firefox/131.0"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.biobiochile.cl/buscador/",
    "Content-Type": "application/json; charset=UTF-8",
}


class BiobbioScraper(BaseApiScraper):
    SOURCE_SLUG = "biobio"
    BATCH_SIZE = 20  # the API returns ~15-20 per call; offset increments by 20 in datamedios

    def _fetch_page(self, query: str, offset: int) -> list[dict]:
        data = self._get(
            API_URL,
            params={
                "offset": offset,
                "search": query,
                "intervalo": "",
                "orden": "ultimas",
            },
            headers=API_HEADERS,
        )
        if not data:
            return []
        return data.get("notas") or []

    def _map_article(self, raw: dict) -> Optional[dict]:
        titulo = unescape(raw.get("post_title") or "").strip()
        body_html = raw.get("post_content") or ""
        bajada = unescape(raw.get("post_excerpt") or "").strip() or None
        url = raw.get("post_URL_https") or raw.get("post_URL") or ""

        # Date: prefer ISO form (raw_post_date "YYYY-MM-DD HH:MM:SS"); fall back
        # to year/month/day fields, then to post_date_date (DD/MM/YYYY).
        fecha = ""
        raw_dt = raw.get("raw_post_date") or ""
        if raw_dt:
            fecha = raw_dt[:10]
        elif raw.get("year") and raw.get("month") and raw.get("day"):
            fecha = f"{raw['year']}-{raw['month']}-{raw['day']}"

        # Strip HTML to plain text body (paragraphs joined with \n)
        cuerpo = _html_to_paragraphs(body_html) if body_html else ""

        if not titulo or len(titulo) < 20:
            return None
        if not cuerpo or len(cuerpo) < 400:
            return None
        if not url:
            return None

        return {
            "titulo": titulo,
            "cuerpo": cuerpo,
            "bajada": bajada,
            "fecha": fecha or None,
            "fuente": self.SOURCE_SLUG,
            "url": url,
            "fecha_scraping": datetime.now().isoformat(timespec="seconds"),
            "query": "",
        }


def _html_to_paragraphs(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # Drop "Lee también" boxes and related-notes scaffolding
    for box in soup.select(".lee-tambien-bbcl, .related-notes, script, style"):
        box.decompose()
    paras = soup.select("p")
    texts = [p.get_text(" ", strip=True) for p in paras]
    return "\n".join(t for t in texts if t)
