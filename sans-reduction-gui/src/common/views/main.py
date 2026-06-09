"""Defines the top-level Trame application."""

import argparse
import logging
from pathlib import Path
from typing import Any

from nova.mvvm.trame_binding import TrameBinding
from nova.trame import ThemedApp
from trame.app import get_server
from trame_server.state import State

from common.mvvm_factory import create_viewmodels
from common.views.execution_panel import ExecutionPanel
from common.views.tab_content_panel import TabContentPanel
from common.views.tabs_panel import TabsPanel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SansGui(ThemedApp):
    """Main class for SANS GUI."""

    def _parse_command_arguments(self) -> Any:
        parser = argparse.ArgumentParser()
        parser.add_argument("--staff-input-file", default=None, help="Path to staff input configuration file")
        parser.add_argument("--config", help="Path to configuration file")
        args, unknown = parser.parse_known_args()
        return args

    def __init__(self, config_class: Any) -> None:
        super().__init__()

        self.server = get_server(None, client_type="vue3")
        binding = TrameBinding(self.server.state)
        args = self._parse_command_arguments()

        js_path = (Path(__file__).parent / "assets" / "js").resolve()
        self.server.enable_module(
            {
                "scripts": ["assets/js/stitching/prepare_charts.js"],
                "serve": {"assets/js/stitching": js_path},
            }
        )

        self.view_models = create_viewmodels(config_class, binding, args)
        self.view_model = self.view_models["main"]
        self.view_model.galaxy_url_bind.connect("galaxy_url")
        self.view_models["execution"].galaxy_running_bind.connect("galaxy_running")

        self.view_model.init_view()
        self.create_ui()

    @property
    def state(self) -> State:
        return self.server.state

    def create_ui(self, user_input_tab: Any = None, staff_input_tab: Any = None) -> Any:
        self.set_theme("CompactTheme")

        with super().create_ui() as layout:
            with layout.pre_content:
                TabsPanel(self.server, self.view_models, user_input_tab, staff_input_tab)

            with layout.content:
                TabContentPanel(self.server, self.view_models, user_input_tab, staff_input_tab)

            with layout.post_content:
                ExecutionPanel(self.server, self.view_models["execution"])

            return layout
