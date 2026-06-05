"""Cooperativa — Prontus CMS, custom search via /cgi-bin/prontus_search.cgi.

The visible search box submits to a CGI script that 302-redirects to a cached
HTML page (/noticias/site/cache/search/pags/searchNNNNNN.html). The cached
page is not directly addressable, but the CGI URL with the right hidden form
params returns the same content via follow-redirect.
"""
import logging
import re
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

from scraper.base import HARD_PAGE_CAP, BaseScraper

logger = logging.getLogger(__name__)

# Article URLs have a /YYYY-MM-DD/ path segment; tax/port/category pages don't.
_ARTICLE_URL_RE = re.compile(r"/\d{4}-\d{2}-\d{2}/")
# Drop these noisy paths that match the broad link selector but aren't articles.
_NON_ARTICLE_PATHS = ("/stat/", "/site/tax/", "/site/edic/", "/site/artic/")

_SEARCH_BASE = "https://www.cooperativa.cl/cgi-bin/prontus_search.cgi"
_SEARCH_DEFAULTS = {
    "search_prontus": "noticias",
    "search_tmp": "search_cooperativa_2018.html",
    "search_modo": "and",
    "search_orden": "cro",
    "search_meta1": "",
    "search_form": "no",
    "search_resxpag": "15",
}


class CooperativaScraper(BaseScraper):
    SOURCE_SLUG = "cooperativa"
    INDEX_URL_TEMPLATE = "https://www.cooperativa.cl/noticias/pais/"
    # Sentinel — search is handled by _collect_urls_search override; the
    # template just needs to be truthy to enable the search path.
    SEARCH_URL_TEMPLATE = _SEARCH_BASE

    @property
    def link_selector(self):
        return "article a[href*='/noticias/'][href$='.html'], .resultado a[href*='/noticias/'][href$='.html']"

    def _extract_links(self, soup: BeautifulSoup) -> list[str]:
        # Apply article-shape filter at the source so feed, search, and `check`
        # all reject category/tax/port URLs uniformly.
        return _filter_article_links(super()._extract_links(soup))

    @property
    def title_selector(self): return "h1"

    @property
    def date_selector(self): return "time"

    @property
    def body_selector(self): return ".cuerpo-articulo p"

    def _collect_urls_search(self, phrase: str, since: date, until: date) -> list[str]:
        """Override: build full querystring (prontus_search.cgi needs the
        whole hidden-input bundle, not just `?q=`)."""
        import requests
        urls: list[str] = []
        for page in range(1, HARD_PAGE_CAP + 1):
            params = dict(_SEARCH_DEFAULTS)
            params["search_texto"] = phrase
            params["search_pag"] = page
            try:
                resp = requests.get(
                    _SEARCH_BASE,
                    params=params,
                    headers=self.HEADERS,
                    timeout=self.REQUEST_TIMEOUT,
                    allow_redirects=True,
                )
            except Exception as e:
                logger.warning(f"[{self.SOURCE_SLUG}] search request error: {e}")
                break
            if resp.status_code != 200:
                logger.debug(f"[{self.SOURCE_SLUG}] search page {page} HTTP {resp.status_code}")
                break
            soup = BeautifulSoup(resp.text, "lxml")
            page_links = self._extract_links(soup)
            if not page_links:
                if page == 1:
                    logger.warning(
                        f"[{self.SOURCE_SLUG}] search returned 0 article links for phrase={phrase!r}"
                    )
                break
            urls.extend(page_links)
            self._polite_delay()
        return list(dict.fromkeys(urls))

    def _collect_urls_feed(self, since: date, until: date) -> list[str]:
        # Listing has no pagination — fetch once
        soup = self._fetch(self.INDEX_URL_TEMPLATE)
        if soup is None:
            return []
        return self._extract_links(soup)

    def _date_text(self, soup) -> Optional[str]:
        # Date is encoded in the article URL: /YYYY-MM-DD/
        return self._url_date_from_soup(soup) or None


def _filter_article_links(links: list[str]) -> list[str]:
    """Keep only real article URLs (pattern: /noticias/{cat}/.../YYYY-MM-DD/{id}.html).
    Drops nav, weather, category, and tag links."""
    out: list[str] = []
    for url in links:
        if "/noticias/" not in url:
            continue
        if any(p in url for p in _NON_ARTICLE_PATHS):
            continue
        if not url.endswith(".html"):
            continue
        if not _ARTICLE_URL_RE.search(url):
            continue
        out.append(url)
    return out
