from scraper.base import BaseScraper


class ElSigloScraper(BaseScraper):
    SOURCE_SLUG = "elsiglo"
    INDEX_URL_TEMPLATE = "https://elsiglo.cl/category/pais/page/{page}"
    SEARCH_URL_TEMPLATE = "https://elsiglo.cl/?s={query}&paged={page}"

    @property
    def link_selector(self): return ".entry-title a"

    @property
    def title_selector(self): return "main .entry-title"

    @property
    def date_selector(self): return "main .entry-meta .date"

    @property
    def body_selector(self): return ".entry-content p"

    @property
    def subtitle_selector(self): return "main blockquote"
