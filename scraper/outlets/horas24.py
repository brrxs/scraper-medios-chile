"""24 Horas (TVN) — Prontus CMS.

Feed: lazy-loading listing page, fetched with Playwright (JS-rendered).
Search: Prontus CGI at /cgi-bin/prontus_search.cgi — returns cached static HTML,
so we use requests directly (bypassing Playwright) for URL collection.
Article pages are JS-rendered → still fetched via Playwright.
"""
import logging
import re
from datetime import date
from typing import Optional

import requests as _requests
from bs4 import BeautifulSoup

from scraper.base import HARD_PAGE_CAP
from scraper.base_playwright import BasePlaywrightScraper

logger = logging.getLogger(__name__)

_SEARCH_BASE = "https://www.24horas.cl/cgi-bin/prontus_search.cgi"
_SEARCH_DEFAULTS = {
    "search_prontus": "24horas",
    "search_tmp": "search.html",
    "search_modo": "and",
    "search_orden": "cro",
    "search_form": "no",
    "search_resxpag": "15",
}

# Non-article paths to reject (Prontus taxonomy/nav pages)
_NON_ARTICLE_PATHS = ("/stat/", "/site/tax/", "/site/edic/", "/site/artic/")


class Horas24Scraper(BasePlaywrightScraper):
    SOURCE_SLUG = "24horas"
    INDEX_URL_TEMPLATE = "https://www.24horas.cl/actualidad/nacional"
    # Sentinel — search handled by _collect_urls_search override.
    SEARCH_URL_TEMPLATE = _SEARCH_BASE

    @property
    def link_selector(self): return "a[href*='/actualidad/']"

    @property
    def title_selector(self): return "h1"

    @property
    def date_selector(self): return ".fecha"

    @property
    def body_selector(self): return ".CUERPO p"

    PW_PAGE_CAP = 8

    def _collect_urls_search(self, phrase: str, since: date, until: date) -> list[str]:
        urls: list[str] = []
        for page in range(1, HARD_PAGE_CAP + 1):
            params = dict(_SEARCH_DEFAULTS)
            params["search_texto"] = phrase
            params["search_pag"] = page
            try:
                resp = _requests.get(
                    _SEARCH_BASE,
                    params=params,
                    headers=self.HEADERS,
                    timeout=self.REQUEST_TIMEOUT,
                    allow_redirects=True,
                )
            except Exception as e:
                logger.warning(f"[{self.SOURCE_SLUG}] search error: {e}")
                break
            if resp.status_code != 200:
                logger.debug(f"[{self.SOURCE_SLUG}] search page {page} HTTP {resp.status_code}")
                break
            soup = BeautifulSoup(resp.text, "lxml")
            links = self._extract_links(soup)
            if not links:
                if page == 1:
                    logger.warning(
                        f"[{self.SOURCE_SLUG}] search page 1 returned 0 links for {phrase!r}"
                    )
                break
            urls.extend(links)
            self._polite_delay()
        return list(dict.fromkeys(urls))

    def _collect_urls_feed(self, since: date, until: date) -> list[str]:
        seen: set[str] = set()
        urls: list[str] = []
        for pg in range(1, self.PW_PAGE_CAP + 1):
            page_url = self.INDEX_URL_TEMPLATE if pg == 1 else f"{self.INDEX_URL_TEMPLATE}/p/{pg}"
            soup = self._pw_get(page_url, scroll=True)
            if soup is None:
                break
            links = self._extract_links(soup)
            new = [u for u in links if u not in seen]
            if not new:
                break
            seen.update(new)
            urls.extend(new)
            self._polite_delay()
        return urls

    def _extract_links(self, soup: BeautifulSoup) -> list[str]:
        base = "https://www.24horas.cl"
        links = []
        for a in soup.select(self.link_selector):
            href = a.get("href", "")
            if not href:
                continue
            full = href if href.startswith("http") else base + href
            path = full.replace(base, "").rstrip("/")
            if any(p in path for p in _NON_ARTICLE_PATHS):
                continue
            # Require at least /actualidad/{section}/{slug}
            parts = [p for p in path.split("/") if p]
            if len(parts) < 3:
                continue
            links.append(full)
        return links
