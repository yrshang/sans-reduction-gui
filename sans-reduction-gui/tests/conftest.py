"""pytest Fixture for setting up the Selenium driver and the server."""

import urllib.request
from functools import partial
from multiprocessing import Process
from time import sleep
from typing import Generator

from pytest import fixture
from selenium.webdriver import Firefox, FirefoxOptions

from biosans import main as biosans_gui
from gpsans import main as gpsans_gui


def _check_url(url: str) -> bool:
    try:
        return urllib.request.urlopen(url).getcode() == 200
    except Exception:
        return False


def _setup_selenium(port: int) -> Firefox:
    max_tries = 30
    target_url = f"http://localhost:{port}"

    while not _check_url(target_url):
        max_tries -= 1
        if max_tries == 0:
            raise RuntimeError("Server failed to start.")

        sleep(1)

    options = FirefoxOptions()
    options.add_argument("-headless")
    options.add_argument("--height=10000")

    driver = Firefox(options=options)
    driver.get(target_url)

    return driver


@fixture(autouse=True, scope="session")
def biosans_driver() -> Generator[Firefox, None, None]:
    port = 8080

    server_process = Process(target=partial(biosans_gui, open_browser=False, port=port))
    server_process.start()

    yield _setup_selenium(port)

    server_process.terminate()


@fixture(autouse=True, scope="session")
def gpsans_driver() -> Generator[Firefox, None, None]:
    port = 8081

    server_process = Process(target=partial(gpsans_gui, open_browser=False, port=port))
    server_process.start()

    yield _setup_selenium(port)

    server_process.terminate()
