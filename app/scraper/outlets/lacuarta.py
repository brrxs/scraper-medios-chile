"""La Cuarta — custom CMS.

Search: La Cuarta's native /?s= redirects to the homepage; the visible search
uses Google CSE (JS-rendered, CAPTCHA-prone). Search is disabled.
Feed: crawl both the /category/cronica/ WP archive and the /chile/ section
listing (political/national news) to cover more coverage areas.
"""
from datetime import date

from scraper.base import HARD_PAGE_CAP, BaseScraper

_FEED_TEMPLATES = [
    "https://www.lacuarta.com/category/cronica/page/{page}",
    "https://www.lacuarta.com/chile/page/{page}/",
]

_FEED_PAGE_CAP = 10  # per category


class LaCuartaScraper(BaseScraper):
    SOURCE_SLUG = "lacuarta"
    INDEX_URL_TEMPLATE = _FEED_TEMPLATES[0]
    SEARCH_URL_TEMPLATE = ""  # /?s= redirects to homepage; GCSE is JS-rendered

    @property
    def link_selector(self): return "a[href*='/noticia/']"

    @property
    def title_selector(self): return "h1"

    @property
    def date_selector(self): return "time"

    @property
    def body_selector(self): return "div[class*='article'] p"

    def _collect_urls_feed(self, since: date, until: date) -> list[str]:
        urls: list[str] = []
        for tmpl in _FEED_TEMPLATES:
            for pg in range(1, _FEED_PAGE_CAP + 1):
                page_url = tmpl.format(page=pg)
                soup = self._fetch(page_url)
                if soup is None:
                    break
                links = self._extract_links(soup)
                if not links:
                    break
                urls.extend(links)
                self._polite_delay()
        return list(dict.fromkeys(urls))
