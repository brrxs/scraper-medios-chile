from datetime import datetime
from typing import Optional

from scraper.base_api import BaseApiScraper

API_BASE = "https://newsapi.ecn.cl/NewsApi/emol/buscador/emol"


class EmolScraper(BaseApiScraper):
    SOURCE_SLUG = "emol"
    BATCH_SIZE = 10

    def _fetch_page(self, query: str, offset: int) -> list[dict]:
        data = self._get(API_BASE, params={"q": query, "size": self.BATCH_SIZE, "from": offset})
        if data is None:
            return []
        try:
            return [hit["_source"] for hit in data["hits"]["hits"]]
        except (KeyError, TypeError):
            return []

    def _map_article(self, raw: dict) -> Optional[dict]:
        titulo = raw.get("titulo", "")
        cuerpo = raw.get("texto", "")
        if not titulo or len(titulo) < 20:
            return None
        if not cuerpo or len(cuerpo) < 400:
            return None

        fecha_raw = raw.get("fechaPublicacion") or raw.get("fechaModificacion")
        fecha = None
        if fecha_raw:
            try:
                fecha = datetime.fromisoformat(
                    fecha_raw.replace("Z", "+00:00")
                ).date().isoformat()
            except Exception:
                pass

        bajada = raw.get("bajada")
        if isinstance(bajada, (dict, list)):
            bajada = None

        return {
            "titulo": titulo,
            "cuerpo": cuerpo,
            "bajada": bajada,
            "fecha": fecha,
            "fuente": self.SOURCE_SLUG,
            "url": raw.get("permalink", ""),
            "fecha_scraping": datetime.now().isoformat(timespec="seconds"),
            "query": "",
        }
