"""Google News — supplementary catch-all source (GNews library backend).

Uses GNews (ranahaani/GNews) which wraps the official Google News RSS endpoint
with Chile/Spanish targeting, automatic URL resolution, and optional proxy support.

503 mitigation: per-day fetch with exponential backoff (3 attempts, 5/15/30s).
  Per-fetch timeout: 45s via ThreadPoolExecutor to catch GNews hangs.
Proxy: set GNEWS_PROXY env var to route requests through a proxy.
Full-text: set GNEWS_FULLTEXT=1 (or use --gn-full flag in run.py) to fetch the
  real article body via parallel async Playwright + trafilatura. Default is RSS
  snippet only. Concurrency: _GN_CONCURRENT pages (default 5).
  Cap: _GN_FULLTEXT_MAX articles enriched per run (default 150, env GNEWS_FULLTEXT_MAX).
"""
import asyncio
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Optional

from bs4 import BeautifulSoup
from gnews import GNews

from scraper.base_api import BaseApiScraper

# Suppress trafilatura/courlan/htmldate INFO chatter — "discarding data" on
# normal no-body pages is expected, not an error worth surfacing at WARNING.
logging.getLogger("trafilatura").setLevel(logging.ERROR)
logging.getLogger("courlan").setLevel(logging.ERROR)
logging.getLogger("htmldate").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

_MAX_PER_DAY = 100
_RETRY_DELAYS = (5, 15, 30)
_RSS_FETCH_TIMEOUT = 45        # seconds — ThreadPoolExecutor timeout per GNews call
_MIN_FULLTEXT_LEN = 100
_GN_CONCURRENT = 5             # parallel Playwright pages during enrichment
_GN_FULLTEXT_MAX = int(os.getenv("GNEWS_FULLTEXT_MAX", "150"))
_GN_PROGRESS_EVERY = 25        # log enrichment progress every N articles
_PW_TIMEOUT = 15_000           # ms per page navigation
_PW_URL_WAIT = 6_000           # ms to wait for URL to leave news.google.com
_PW_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
# Standard Google consent cookie — bypasses consent.google.com interstitials
_GOOGLE_CONSENT_COOKIE = {
    "name": "SOCS",
    "value": "CAESEwgDEgk4NjU4OTA1MjIaAmVzIAEaBgiA_LyxBg",
    "domain": ".google.com",
    "path": "/",
}


class GoogleNewsScraper(BaseApiScraper):
    SOURCE_SLUG = "google_news"

    def _collect_for_phrase(self, phrase: str, since: date, until: date) -> list[dict]:
        proxy = os.getenv("GNEWS_PROXY")
        fulltext = bool(os.getenv("GNEWS_FULLTEXT"))

        # Step 1: collect RSS items (fast, sync)
        articles = self._collect_rss(phrase, since, until, proxy)

        # Step 2: enrich in parallel if requested
        if fulltext and articles:
            cap = _GN_FULLTEXT_MAX
            if len(articles) > cap:
                logger.warning(
                    f"[{self.SOURCE_SLUG}] {len(articles)} articles collected — "
                    f"enriching first {cap} with full text, remaining {len(articles) - cap} "
                    f"will keep RSS snippet (set GNEWS_FULLTEXT_MAX to override)"
                )
                to_enrich, rest = articles[:cap], articles[cap:]
            else:
                to_enrich, rest = articles, []

            try:
                enriched = asyncio.run(_enrich_batch_async(to_enrich, proxy, self.SOURCE_SLUG))
            except Exception as e:
                logger.warning(f"[{self.SOURCE_SLUG}] async enrichment failed ({e}), keeping RSS snippets")
                enriched = to_enrich

            articles = enriched + rest

        return articles

    def _collect_rss(self, phrase: str, since: date, until: date, proxy: Optional[str]) -> list[dict]:
        results: list[dict] = []
        seen: set[str] = set()
        day = since
        while day <= until:
            for article in self._fetch_day(phrase, day, proxy):
                url = article.get("url") or ""
                if url and url not in seen:
                    seen.add(url)
                    results.append(article)
            time.sleep(random.uniform(1.0, 2.5))
            day += timedelta(days=1)
        return results

    def _fetch_day(self, phrase: str, day: date, proxy: Optional[str]) -> list[dict]:
        next_day = day + timedelta(days=1)
        client = GNews(
            language="es",
            country="CL",
            max_results=_MAX_PER_DAY,
            start_date=(day.year, day.month, day.day),
            end_date=(next_day.year, next_day.month, next_day.day),
        )
        if proxy:
            client.proxy = {"http": proxy, "https": proxy}

        for attempt in range(len(_RETRY_DELAYS) + 1):
            try:
                # Guard against GNews hanging indefinitely on a single day-fetch
                with ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(client.get_news, phrase)
                    try:
                        raw_list = future.result(timeout=_RSS_FETCH_TIMEOUT)
                    except FuturesTimeoutError:
                        raise TimeoutError(f"GNews fetch timed out after {_RSS_FETCH_TIMEOUT}s")

                n = len(raw_list)
                logger.info(f"[{self.SOURCE_SLUG}] {day} query={phrase!r} -> {n} results")
                if n >= _MAX_PER_DAY:
                    logger.warning(
                        f"[{self.SOURCE_SLUG}] 100-result cap hit on {day} for query={phrase!r} — "
                        f"add more --query phrases for broader coverage"
                    )
                return [a for a in (_gnews_to_article(r, self.SOURCE_SLUG) for r in raw_list) if a]
            except Exception as e:
                if attempt < len(_RETRY_DELAYS):
                    delay = _RETRY_DELAYS[attempt] + random.uniform(-2, 2)
                    logger.warning(
                        f"[{self.SOURCE_SLUG}] attempt {attempt + 1} failed ({e}), "
                        f"retrying in {delay:.0f}s"
                    )
                    time.sleep(delay)
                else:
                    logger.warning(f"[{self.SOURCE_SLUG}] all retries exhausted on {day}: {e}")
        return []

    def _fetch_page(self, query: str, offset: int) -> list[dict]:
        """Used only by run.py `check` command — returns raw GNews dicts for today."""
        if offset > 0:
            return []
        client = GNews(language="es", country="CL", max_results=10)
        try:
            return client.get_news(query or "chile")
        except Exception as e:
            logger.warning(f"[{self.SOURCE_SLUG}] check fetch failed: {e}")
            return []

    def _map_article(self, raw: dict) -> Optional[dict]:
        return _gnews_to_article(raw, self.SOURCE_SLUG)


async def _enrich_batch_async(
    articles: list[dict], proxy: Optional[str], slug: str = "google_news"
) -> list[dict]:
    """Resolve Google News URLs and extract full article text in parallel.

    Opens _GN_CONCURRENT Playwright pages simultaneously. Each page navigates
    to a Google News URL with domcontentloaded (not networkidle) to avoid hanging
    on ad-heavy pages, waits for the JS redirect to the real article, then
    extracts body text with trafilatura. Falls back to the original article dict
    on any failure so no articles are lost.
    """
    from playwright.async_api import async_playwright
    import trafilatura

    counter = {"done": 0}
    total = len(articles)

    browser = None
    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent=_PW_USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="es-CL",
            )
            # Bypass Google consent interstitials
            await ctx.add_cookies([_GOOGLE_CONSENT_COOKIE])

            sem = asyncio.Semaphore(_GN_CONCURRENT)

            async def enrich_one(article: dict) -> dict:
                async with sem:
                    try:
                        page = await ctx.new_page()
                        try:
                            result = await _enrich_async(page, article, trafilatura)
                        finally:
                            await page.close()
                    except Exception as e:
                        logger.debug(f"[{slug}] page error, keeping RSS snippet: {e}")
                        result = article

                    counter["done"] += 1
                    done = counter["done"]
                    if done % _GN_PROGRESS_EVERY == 0 or done == total:
                        logger.info(f"[{slug}] enriched {done}/{total}")
                    return result

            tasks = [enrich_one(a) for a in articles]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass

    # Swap any exception/non-dict results back to the original article
    results = []
    for orig, res in zip(articles, raw_results):
        if isinstance(res, dict):
            results.append(res)
        else:
            results.append(orig)
    return results


async def _enrich_async(page, article: dict, trafilatura) -> dict:
    url = article.get("url") or ""
    if not url:
        return article
    try:
        # domcontentloaded is much faster than networkidle on ad-heavy news sites
        await page.goto(url, wait_until="domcontentloaded", timeout=_PW_TIMEOUT)

        # Wait for the JS redirect to leave news.google.com
        if "news.google.com" in page.url:
            try:
                await page.wait_for_url(
                    lambda u: "news.google.com" not in u, timeout=_PW_URL_WAIT
                )
            except Exception:
                pass

        # Also catches consent.google.com that slipped past the cookie
        if "news.google.com" in page.url or "consent.google.com" in page.url:
            logger.debug(f"[google_news] URL not resolved: {url[:60]}")
            return article

        # Let the destination page settle briefly (best-effort)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=3_000)
        except Exception:
            pass

        html = await page.content()
        text = (await asyncio.to_thread(
            trafilatura.extract,
            html,
            url=url,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        ) or "").strip()

        if text and len(text) >= _MIN_FULLTEXT_LEN:
            article = dict(article)
            article["cuerpo"] = text
            logger.debug(f"[google_news] fulltext ok: {len(text)} chars | {page.url[:60]}")
        else:
            logger.debug(f"[google_news] fulltext too short ({len(text) if text else 0}ch) | {page.url[:60]}")
    except Exception as e:
        logger.debug(f"[google_news] fulltext failed for {url[:60]}: {e}")
    return article


def _gnews_to_article(raw: dict, slug: str) -> Optional[dict]:
    titulo = (raw.get("title") or "").strip()
    if not titulo or len(titulo) < 20:
        return None
    url = raw.get("url") or ""
    if not url:
        return None

    publisher = raw.get("publisher") or {}
    source_name = (publisher.get("title") or "").strip() or slug

    raw_desc = raw.get("description") or ""
    description = BeautifulSoup(raw_desc, "lxml").get_text(" ", strip=True) if raw_desc else ""
    if description and source_name != slug:
        bajada: Optional[str] = f"[{source_name}] {description}"[:500]
    else:
        bajada = description[:500] if description else None
    cuerpo = bajada or titulo

    fecha = _parse_gnews_date(raw.get("published date") or "")

    return {
        "titulo": titulo,
        "cuerpo": cuerpo,
        "bajada": bajada,
        "fecha": fecha,
        "fuente": source_name,
        "url": url,
        "fecha_scraping": datetime.now().isoformat(timespec="seconds"),
        "query": "",
    }


def _parse_gnews_date(date_str: str) -> Optional[str]:
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str).date().isoformat()
    except Exception:
        return None
