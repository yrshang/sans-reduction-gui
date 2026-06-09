"""View model for main view."""

import argparse
from typing import Any

from nova.mvvm.interface import BindingInterface

from common.models.main import MainModel


class MainViewModel:
    """Main view model."""

    def _parse_args(self) -> Any:
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", help="Path to configuration file")
        args, unknown = parser.parse_known_args()
        return args

    def __init__(self, model: MainModel, binding: BindingInterface, args: Any) -> None:
        self.model = model
        self.galaxy_current_history = None

        self.galaxy_url_bind = binding.new_bind()

        if args.config:
            self.model.load_config(open(args.config).read())

    def init_view(self) -> None:
        self.galaxy_url_bind.update_in_view(self.model._galaxy.galaxy_url)

    def prepare_config_file(self) -> Any:
        return self.model.prepare_config_file()

    def load_config(self, data: Any) -> None:
        self.model.load_config(data)
