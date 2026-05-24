import abc
import logging
import random
import re
import time
from datetime import date, datetime, timedelta
from typing import Optional
from urllib.parse import quote, quote_plus

import requests
from bs4 import BeautifulSoup

from scraper.output import save_articles
from scraper.utils import any_phrase_matches, clean_text, parse_date

logger = logging.getLogger(__name__)

MIN_TITULO_LEN = 20
MIN_CUERPO_LEN = 400
HARD_PAGE_CAP = 50


class BaseScraper(abc.ABC):
    SOURCE_SLUG: str = ""
    INDEX_URL_TEMPLATE: str = ""
    SEARCH_URL_TEMPLATE: str = ""
    DELAY_MIN: float = 1.5
    DELAY_MAX: float = 3.5
    REQUEST_TIMEOUT: int = 20
    HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; prensa_chile_py/1.0; +https://github.com)"}

    # --- Selectors (subclasses must define) ---

    @property
    @abc.abstractmethod
    def link_selector(self) -> str: ...

    @property
    @abc.abstractmethod
    def title_selector(self) -> str: ...

    @property
    @abc.abstractmethod
    def date_selector(self) -> str: ...

    @property
    @abc.abstractmethod
    def body_selector(self) -> str: ...

    @property
    def subtitle_selector(self) -> Optional[str]:
        return None

    # --- Public entry point ---

    def run(
        self,
        queries: Optional[list[str]] = None,
        since: Optional[date] = None,
        until: Optional[date] = None,
    ) -> list[dict]:
        since = since or (date.today() - timedelta(days=7))
        until = until or date.today()
        queries = [q for q in (queries or []) if q and q.strip()]

        logger.info(f"[{self.SOURCE_SLUG}] since={since} until={until} queries={queries!r}")

        if queries:
            all_urls: list[str] = []
            for phrase in queries:
                phrase_urls = self._collect_urls_search(phrase, since, until)
                logger.info(f"[{self.SOURCE_SLUG}] search phrase={phrase!r} -> {len(phrase_urls)} URLs")
                all_urls.extend(phrase_urls)
            all_urls = list(dict.fromkeys(all_urls))

            if not all_urls:
                logger.info(f"[{self.SOURCE_SLUG}] all searches empty, falling back to feed + filter")
                all_urls = self._collect_urls_feed(since, until)

            articles = self._scrape_urls(all_urls)
            articles = [a for a in articles if any_phrase_matches(
                (a.get("titulo") or "") + " " + (a.get("cuerpo") or ""), queries
            )]
        else:
            urls = self._collect_urls_feed(since, until)
            articles = self._scrape_urls(urls)

        # Final date filter (belt-and-suspenders)
        articles = [a for a in articles if _in_window(a.get("fecha"), since, until)]
        query_label = ", ".join(queries)
        for a in articles:
            a["query"] = query_label

        logger.info(f"[{self.SOURCE_SLUG}] {len(articles)} articles collected")
        if articles:
            save_articles(articles, self.SOURCE_SLUG)
        return articles

    # --- URL collection ---

    def _encode_query(self, phrase: str) -> str:
        """Encode a search phrase for the URL. Default: quote_plus ('+' for space).
        Override (e.g. return quote(phrase)) for sites with slug-style paths that
        need %20 instead of +."""
        return quote_plus(phrase)

    def _collect_urls_search(self, phrase: str, since: date, until: date) -> list[str]:
        if not self.SEARCH_URL_TEMPLATE:
            return []
        q = self._encode_query(phrase)
        urls: list[str] = []
        for page in range(1, HARD_PAGE_CAP + 1):
            page_url = self.SEARCH_URL_TEMPLATE.format(query=q, page=page)
            soup = self._fetch(page_url)
            if soup is None:
                break
            links = self._extract_links(soup)
            if not links:
                if page == 1:
                    logger.warning(
                        f"[{self.SOURCE_SLUG}] search page 1 returned 0 links — "
                        f"endpoint may be broken: {page_url}"
                    )
                break
            urls.extend(links)
            self._polite_delay()
        return list(dict.fromkeys(urls))

    def _collect_urls_feed(self, since: date, until: date) -> list[str]:
        urls: list[str] = []
        for page in range(1, HARD_PAGE_CAP + 1):
            page_url = self.INDEX_URL_TEMPLATE.format(page=page)
            soup = self._fetch(page_url)
            if soup is None:
                break
            links = self._extract_links(soup)
            if not links:
                break
            urls.extend(links)
            self._polite_delay()
        return list(dict.fromkeys(urls))

    # --- Article scraping ---

    def _scrape_urls(self, urls: list[str]) -> list[dict]:
        logger.info(f"[{self.SOURCE_SLUG}] scraping {len(urls)} URLs...")
        articles = []
        past_cutoff_count = 0
        for url in urls:
            result = self._scrape_article_safe(url)
            if result:
                articles.append(result)
                if result.get("fecha"):
                    d = parse_date(result["fecha"])
                    # Track consecutive old articles to stop early
                    if d and d < _today_minus(90):
                        past_cutoff_count += 1
                        if past_cutoff_count >= 5:
                            logger.info(f"[{self.SOURCE_SLUG}] 5+ very old articles, stopping early")
                            break
                    else:
                        past_cutoff_count = 0
            self._polite_delay()
        return articles

    def _scrape_article_safe(self, url: str) -> Optional[dict]:
        try:
            return self._scrape_article(url)
        except Exception as e:
            logger.warning(f"[{self.SOURCE_SLUG}] failed {url}: {e}")
            return None

    def _scrape_article(self, url: str) -> Optional[dict]:
        soup = self._fetch(url)
        if soup is None:
            return None

        titulo = self._text(soup, self.title_selector)
        cuerpo = self._paragraphs(soup, self.body_selector)
        fecha_raw = self._date_text(soup)
        bajada = self._text(soup, self.subtitle_selector) if self.subtitle_selector else None

        if not titulo or len(titulo) < MIN_TITULO_LEN:
            return None
        if not cuerpo or len(cuerpo) < MIN_CUERPO_LEN:
            return None

        fecha_obj = parse_date(fecha_raw) if fecha_raw else None

        return {
            "titulo": clean_text(titulo),
            "cuerpo": clean_text(cuerpo),
            "bajada": clean_text(bajada) if bajada else None,
            "fecha": fecha_obj.isoformat() if fecha_obj else None,
            "fuente": self.SOURCE_SLUG,
            "url": url,
            "fecha_scraping": datetime.now().isoformat(timespec="seconds"),
            "query": "",
        }

    def _date_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract date text. Override for sites that use <time datetime="...">."""
        el = soup.select_one(self.date_selector)
        if el is None:
            return None
        # Prefer datetime attribute (ISO format) over visible text
        dt_attr = el.get("datetime")
        if dt_attr:
            return dt_attr
        return el.get_text(strip=True)

    # --- HTTP ---

    def _fetch(self, url: str) -> Optional[BeautifulSoup]:
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=self.REQUEST_TIMEOUT)
            if resp.status_code != 200:
                logger.debug(f"[{self.SOURCE_SLUG}] HTTP {resp.status_code} {url}")
                return None
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as e:
            logger.warning(f"[{self.SOURCE_SLUG}] request error {url}: {e}")
            return None

    def _extract_links(self, soup: BeautifulSoup) -> list[str]:
        anchors = soup.select(self.link_selector)
        links = []
        for a in anchors:
            href = a.get("href", "")
            if href and href.startswith("http"):
                links.append(href)
            elif href and href.startswith("/"):
                # Reconstruct absolute URL from the base domain
                base = self._base_url()
                if base:
                    links.append(base.rstrip("/") + href)
        return links

    def _meta_date(self, soup: BeautifulSoup) -> Optional[str]:
        for selector, attr in [
            ('meta[property="article:published_time"]', "content"),
            ('meta[name="publish_date"]', "content"),
        ]:
            el = soup.select_one(selector)
            if el:
                val = el.get(attr, "").strip()
                if val:
                    return val
        return None

    def _url_date_from_soup(self, soup: BeautifulSoup) -> Optional[str]:
        canonical = soup.select_one("link[rel='canonical']")
        url = canonical.get("href", "") if canonical else ""
        m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        m = re.search(r"/(\d{4}-\d{2}-\d{2})/", url)
        return m.group(1) if m else None

    def _base_url(self) -> str:
        """Extract scheme+host from INDEX_URL_TEMPLATE."""
        m = re.match(r"(https?://[^/]+)", self.INDEX_URL_TEMPLATE)
        return m.group(1) if m else ""

    # --- Helpers ---

    def _text(self, soup: BeautifulSoup, selector: Optional[str]) -> Optional[str]:
        if not selector:
            return None
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    def _paragraphs(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        paras = soup.select(selector)
        text = "\n".join(p.get_text(strip=True) for p in paras if p.get_text(strip=True))
        return text if text else None

    def _polite_delay(self):
        time.sleep(random.uniform(self.DELAY_MIN, self.DELAY_MAX))


def _in_window(fecha_str: Optional[str], since: date, until: date) -> bool:
    if not fecha_str:
        return True  # keep articles with unparseable dates rather than discard
    d = parse_date(fecha_str)
    if d is None:
        return True
    return since <= d <= until


def _today_minus(days: int) -> date:
    return date.today() - timedelta(days=days)
