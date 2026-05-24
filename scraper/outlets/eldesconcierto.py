"""El Desconcierto — feed-only outlet.

Search is intentionally disabled: the public ?s= URL returns the homepage, and
the visible "Resultado de búsqueda" page is a JS-rendered Google Programmable
Search Engine that doesn't initialize from URL hash params in headless mode and
falls back to ~1 result. WordPress REST is disabled. So instead of pretending
to support search, we crawl several category index pages (each yields ~16
article URLs) and let the BaseScraper apply the query filter against
title+body. With 4–5 categories the candidate pool is ~60–80 articles.
"""
import logging
import re
from datetime import date
from typing import Optional

from scraper.base import BaseScraper

logger = logging.getLogger(__name__)

_CAT_PAGE_CAP = 3  # paginate each category up to this many pages

# Category pages that each surface ~16 recent article URLs. /actualidad covers
# the political/news beat; the others backfill thematic coverage.
_CATEGORY_URLS = [
    "https://eldesconcierto.cl/actualidad",
    "https://eldesconcierto.cl/entrevistas",
    "https://eldesconcierto.cl/medio-ambiente",
    "https://eldesconcierto.cl/hoja-de-ruta",
    "https://eldesconcierto.cl/crisis-ecologica",
]

# Article URL shapes:
#   New: /{category}/{slug}-n{digits}
#   Old: /{YYYY}/{MM}/{DD}/{slug}
_ARTICLE_RE = re.compile(
    r"eldesconcierto\.cl/(?:[a-z0-9-]+/[a-z0-9-]+-n\d+|\d{4}/\d{2}/\d{2}/[a-z0-9-]+)/?$"
)


class ElDesconciertoScraper(BaseScraper):
    SOURCE_SLUG = "eldesconcierto"
    INDEX_URL_TEMPLATE = _CATEGORY_URLS[0]
    # Search disabled — see module docstring.
    SEARCH_URL_TEMPLATE = ""

    @property
    def link_selector(self):
        # Broad — we filter to real article URLs in _collect_urls_feed.
        return "a[href*='eldesconcierto.cl/']"

    @property
    def title_selector(self): return "h1"

    @property
    def date_selector(self): return ".news-headline__date"

    @property
    def body_selector(self): return "article p"

    def _collect_urls_feed(self, since: date, until: date) -> list[str]:
        urls: list[str] = []
        for cat_url in _CATEGORY_URLS:
            for pg in range(1, _CAT_PAGE_CAP + 1):
                page_url = cat_url if pg == 1 else f"{cat_url}/page/{pg}/"
                soup = self._fetch(page_url)
                if soup is None:
                    break
                new_urls = [
                    u for u in self._extract_links(soup) if _ARTICLE_RE.search(u)
                ]
                if not new_urls:
                    break  # 404 or empty page — stop paginating this category
                urls.extend(new_urls)
                self._polite_delay()
        return list(dict.fromkeys(urls))

    def _date_text(self, soup) -> Optional[str]:
        # Try the standard selector; fall back to OG meta if missing.
        el = soup.select_one(self.date_selector)
        if el is not None:
            dt_attr = el.get("datetime") or el.get_text(strip=True)
            if dt_attr:
                return dt_attr
        return self._meta_date(soup)
