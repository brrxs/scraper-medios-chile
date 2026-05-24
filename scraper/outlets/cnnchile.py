from urllib.parse import quote

from scraper.base import BaseScraper


class CnnChileScraper(BaseScraper):
    SOURCE_SLUG = "cnnchile"
    INDEX_URL_TEMPLATE = "https://www.cnnchile.com/pais/page/{page}"
    # Slug-style path: needs %20 for space (quote, not quote_plus).
    # Verified: /buscador/mara%20sedini/ -> 3 result pages; /buscador/mara+sedini/ -> 1 (broken).
    SEARCH_URL_TEMPLATE = "https://www.cnnchile.com/buscador/{query}/page/{page}/"

    def _encode_query(self, phrase: str) -> str:
        return quote(phrase, safe="")

    @property
    def link_selector(self): return "article a[href]"

    @property
    def title_selector(self): return "h1"

    @property
    def date_selector(self): return "time"

    @property
    def body_selector(self): return "div.main-article__text p"
