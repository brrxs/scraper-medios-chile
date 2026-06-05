from scraper.outlets.elsiglo import ElSigloScraper
from scraper.outlets.elmostrador import ElMostradorScraper
from scraper.outlets.ciper import CiperScraper
from scraper.outlets.eldesconcierto import ElDesconciertoScraper
from scraper.outlets.elciudadano import ElCiudadanoScraper
from scraper.outlets.biobio import BiobbioScraper
from scraper.outlets.cooperativa import CooperativaScraper
from scraper.outlets.cnnchile import CnnChileScraper
from scraper.outlets.lanacion import LaNacionScraper
from scraper.outlets.t13 import T13Scraper
from scraper.outlets.horas24 import Horas24Scraper
from scraper.outlets.chvnoticias import ChvNoticiasScraper
from scraper.outlets.meganoticias import MegaNoticiasScraper
from scraper.outlets.lacuarta import LaCuartaScraper
from scraper.outlets.emol import EmolScraper
from scraper.outlets.google_news import GoogleNewsScraper

REGISTRY: dict[str, type] = {
    "elsiglo": ElSigloScraper,
    "elmostrador": ElMostradorScraper,
    "ciper": CiperScraper,
    "eldesconcierto": ElDesconciertoScraper,
    "elciudadano": ElCiudadanoScraper,
    "biobio": BiobbioScraper,
    "cooperativa": CooperativaScraper,
    "cnnchile": CnnChileScraper,
    "lanacion": LaNacionScraper,
    "t13": T13Scraper,
    "24horas": Horas24Scraper,
    "chvnoticias": ChvNoticiasScraper,
    "meganoticias": MegaNoticiasScraper,
    "lacuarta": LaCuartaScraper,
    "emol": EmolScraper,
    "google_news": GoogleNewsScraper,
}
