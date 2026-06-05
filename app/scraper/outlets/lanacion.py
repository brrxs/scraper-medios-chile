from scraper.base import BaseScraper


class LaNacionScraper(BaseScraper):
    SOURCE_SLUG = "lanacion"
    REQUEST_TIMEOUT = 10  # site hangs connections; fail fast
    INDEX_URL_TEMPLATE = "https://www.lanacion.cl/category/pais/page/{page}"
    SEARCH_URL_TEMPLATE = "https://www.lanacion.cl/?s={query}&paged={page}"

    @property
    def link_selector(self): return ".entry-title a"

    @property
    def title_selector(self): return "h1"

    @property
    def date_selector(self): return ".entry-date"

    @property
    def body_selector(self): return "div.tdc-content-wrap p"
