import logging
from typing import Optional

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class BasePlaywrightScraper(BaseScraper):
    """BaseScraper variant that renders pages with a headless Chromium browser."""

    WAIT_UNTIL = "domcontentloaded"
    PAGE_TIMEOUT = 30_000  # ms

    def run(self, queries=None, since=None, until=None):
        with sync_playwright() as pw:
            self._browser = pw.chromium.launch(headless=True)
            try:
                return super().run(queries=queries, since=since, until=until)
            finally:
                self._browser.close()
                self._browser = None

    def _fetch(self, url: str) -> Optional[BeautifulSoup]:
        return self._pw_get(url, scroll=False)

    def _pw_get(self, url: str, scroll: bool = False) -> Optional[BeautifulSoup]:
        ctx = None
        try:
            ctx = self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = ctx.new_page()
            page.goto(url, wait_until=self.WAIT_UNTIL, timeout=self.PAGE_TIMEOUT)
            if scroll:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
            return BeautifulSoup(page.content(), "lxml")
        except Exception as e:
            logger.warning(f"[{self.SOURCE_SLUG}] playwright error {url}: {e}")
            return None
        finally:
            if ctx is not None:
                ctx.close()
