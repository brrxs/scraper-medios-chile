import re
from typing import Optional

from bs4 import BeautifulSoup

from scraper.base import BaseScraper

_RE_DATE = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/")


class CiperScraper(BaseScraper):
    SOURCE_SLUG = "ciper"
    INDEX_URL_TEMPLATE = "https://www.ciperchile.cl/actualidad/page/{page}"
    SEARCH_URL_TEMPLATE = "https://www.ciperchile.cl/?s={query}&paged={page}"

    @property
    def link_selector(self): return "a.alticle-link"  # typo is in their source HTML

    @property
    def title_selector(self): return "h1.article-big-text__title"

    @property
    def date_selector(self): return "time"

    @property
    def body_selector(self): return "div.col-lg-9 p"

    def _date_text(self, soup: BeautifulSoup) -> Optional[str]:
        # Date is encoded in the canonical URL: /YYYY/MM/DD/
        canonical = soup.select_one("link[rel='canonical']")
        url = canonical.get("href", "") if canonical else ""
        m = _RE_DATE.search(url)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        return None
