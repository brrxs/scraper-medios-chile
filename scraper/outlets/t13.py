from datetime import date

from scraper.base_playwright import BasePlaywrightScraper


class T13Scraper(BasePlaywrightScraper):
    SOURCE_SLUG = "t13"
    INDEX_URL_TEMPLATE = "https://www.t13.cl/"
    SEARCH_URL_TEMPLATE = "https://www.t13.cl/search?q={query}&page={page}"

    @property
    def link_selector(self): return "a[href*='/noticia/']"

    @property
    def title_selector(self): return "h1"

    @property
    def date_selector(self): return "time[itemprop='datePublished']"

    @property
    def body_selector(self): return ".cuerpo p"

    @property
    def subtitle_selector(self): return ".bajada"

    def _collect_urls_feed(self, since: date, until: date) -> list[str]:
        # t13 has no working paginated listing; homepage has ~50 recent articles
        soup = self._fetch(self.INDEX_URL_TEMPLATE)
        if soup is None:
            return []
        return self._extract_links(soup)
