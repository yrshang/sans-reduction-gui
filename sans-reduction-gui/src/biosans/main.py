"""Entrypoint for the BioSANS GUI."""

import os
import sys
from typing import Any

from dotenv import load_dotenv

from biosans.views.main import BioSansGui
from common.exceptions import ConfigError


def main(**kwargs: Any) -> None:
    load_dotenv()

    os.environ["INSTRUMENT"] = "biosans"
    try:
        app = BioSansGui()
        for arg in sys.argv[1:]:
            try:
                key, value = arg.split("=")
                kwargs[key] = int(value)
            except Exception:
                pass
        app.server.start(**kwargs)
    except ConfigError as e:
        print("Failed to load configuration: ", e)


if __name__ == "__main__":
    main(port=8080, host="0.0.0.0", open_browser=False)
