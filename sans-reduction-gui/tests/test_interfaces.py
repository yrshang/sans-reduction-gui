"""Test the GUIs via Selenium."""

from selenium.webdriver import Firefox
from selenium.webdriver.support.wait import WebDriverWait


def test_interfaces(biosans_driver: Firefox, gpsans_driver: Firefox) -> None:
    WebDriverWait(biosans_driver, 10).until(lambda *args: biosans_driver.title == "Bio-SANS Data Reduction")
    WebDriverWait(gpsans_driver, 10).until(lambda *args: gpsans_driver.title == "GP-SANS Data Reduction")
