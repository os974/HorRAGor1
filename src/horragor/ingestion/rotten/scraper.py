"""
Fetch des pages Rotten Tomatoes via Selenium (couche I/O, isolée du parsing).

POURQUOI Selenium (et pas `requests`) ?
Les scores RT (Tomatometer, Popcornmeter) et le consensus sont injectés par
JavaScript dans des web components (`<media-scorecard>`, `<rt-text>`). Une
simple requête HTTP ne verrait que le squelette HTML sans ces valeurs : il faut
un vrai navigateur qui exécute le JS, d'où Selenium (« extraction dynamique »
exigée par le brief).

Ce module ne fait QUE récupérer le HTML rendu. Le parsing est délégué à
`parser.py` pour rester testable hors-ligne.
"""

from __future__ import annotations

import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from horragor.config.settings import (
    ROTTEN_BASE_URL,
    ROTTEN_PAGE_TIMEOUT,
    ROTTEN_REQUEST_DELAY,
)

logger = logging.getLogger(__name__)

# User-agent réaliste : RT renvoie une page dégradée (ou un mur anti-bot) aux
# clients qui s'annoncent comme automates.
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def _build_driver(headless: bool) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    # --no-sandbox / --disable-dev-shm-usage : indispensables en environnement
    # conteneurisé/CI où le sandbox Chrome et /dev/shm sont restreints.
    for arg in (
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1920,1080",
        f"user-agent={_USER_AGENT}",
    ):
        opts.add_argument(arg)
    return webdriver.Chrome(options=opts)


class RottenScraper:
    """Pilote Selenium réutilisable (un seul navigateur pour N pages)."""

    def __init__(self, headless: bool = True, timeout: int = ROTTEN_PAGE_TIMEOUT):
        self.timeout = timeout
        self.driver = _build_driver(headless)

    # Support du `with` : garantit la fermeture du navigateur même en cas d'erreur.
    def __enter__(self) -> RottenScraper:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        try:
            self.driver.quit()
        except Exception:  # noqa: BLE001 — fermeture best-effort
            pass

    def fetch_movie_html(self, slug: str) -> str | None:
        """
        Charge la page d'un film et renvoie le HTML rendu (ou None si échec).

        On attend explicitement la présence du `media-scorecard` : c'est le
        signal que le JS a injecté les scores. Sans cette attente, on lirait un
        DOM incomplet (scores manquants).
        """
        url = f"{ROTTEN_BASE_URL}/m/{slug}"
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "media-scorecard"))
            )
            time.sleep(ROTTEN_REQUEST_DELAY)  # politesse + fin de rendu
            return self.driver.page_source
        except Exception as e:  # noqa: BLE001
            # Page absente, mur anti-bot, timeout JS... : on log et on continue.
            logger.warning("Échec scraping '%s' (%s)", slug, type(e).__name__)
            return None
