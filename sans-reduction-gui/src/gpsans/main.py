"""Entrypoint for the BioSANS GUI."""

import os
import sys
from typing import Any

from dotenv import load_dotenv

from common.exceptions import ConfigError
from gpsans.views.main import GpSansGui


def main(**kwargs: Any) -> None:
    load_dotenv()

    os.environ["INSTRUMENT"] = "gpsans"
    try:
        app = GpSansGui()
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
    port = int(os.environ.get("SANS_GUI_PORT", 17685))
    main(port=port, host="0.0.0.0", open_browser=False)
