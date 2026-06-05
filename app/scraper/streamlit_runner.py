from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Callable, Optional

from scraper.outlets import REGISTRY


def run_outlets_parallel(
    outlets: list[str],
    queries: list[str],
    since: date,
    until: date,
    n_workers: int = 3,
    on_result: Optional[Callable] = None,
) -> list[dict]:
    """Run multiple outlet scrapers in parallel using threads.

    on_result(slug, articles, error) is called from worker threads as each
    outlet completes — safe to update st.empty() placeholders from it.
    """
    all_articles: list[dict] = []

    def _run(slug: str):
        scraper = REGISTRY[slug]()
        articles = scraper.run(queries=queries, since=since, until=until)
        return slug, articles or []

    with ThreadPoolExecutor(max_workers=n_workers) as ex:
        futures = {ex.submit(_run, slug): slug for slug in outlets}
        for future in as_completed(futures):
            slug = futures[future]
            try:
                _, articles = future.result()
                error = None
            except Exception as e:
                articles = []
                error = str(e)
            all_articles.extend(articles)
            if on_result:
                on_result(slug, articles, error)

    return all_articles
