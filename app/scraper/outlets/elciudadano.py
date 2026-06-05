from typing import Optional

from bs4 import BeautifulSoup

from scraper.base import BaseScraper


class ElCiudadanoScraper(BaseScraper):
    SOURCE_SLUG = "elciudadano"
    INDEX_URL_TEMPLATE = "https://www.elciudadano.com/page/{page}"
    SEARCH_URL_TEMPLATE = "https://www.elciudadano.com/?s={query}&paged={page}"

    @property
    def link_selector(self): return "article a[href*='elciudadano.com']"

    @property
    def title_selector(self): return "h1"

    @property
    def date_selector(self): return "time"

    @property
    def body_selector(self): return "div[class*='content'] p"

    def _date_text(self, soup: BeautifulSoup) -> Optional[str]:
        # 1. Open Graph meta tag (most reliable — WordPress always publishes this)
        val = self._meta_date(soup)
        if val:
            return val
        # 2. <time datetime="..."> attribute
        el = soup.select_one(self.date_selector)
        if el is not None:
            dt_attr = el.get("datetime")
            if dt_attr:
                return dt_attr
            text = el.get_text(strip=True)
            if text:
                return text
        # 3. URL path /YYYY/MM/DD/
        return self._url_date_from_soup(soup)
