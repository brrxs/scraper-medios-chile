from scraper.base import BaseScraper


class ElMostradorScraper(BaseScraper):
    SOURCE_SLUG = "elmostrador"
    INDEX_URL_TEMPLATE = "https://www.elmostrador.cl/noticias/pais/?paged={page}"
    SEARCH_URL_TEMPLATE = "https://www.elmostrador.cl/?s={query}&paged={page}"

    @property
    def link_selector(self): return "a[href*='elmostrador.cl/noticias/'][href*='/20']"

    @property
    def title_selector(self): return "h1.d-the-single__title"

    @property
    def date_selector(self): return "time"

    @property
    def body_selector(self): return "div.js-content-static__article p"
