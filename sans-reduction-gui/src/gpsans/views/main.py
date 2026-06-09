"""Defines the top-level GPSANS GUI."""

from typing import Any

from trame.ui.vuetify3 import VAppLayout

from common.views.main import SansGui
from gpsans.models.config import SharedConfig
from gpsans.views.staff_input_tab import StaffInputTab
from gpsans.views.user_input_tab import UserInputTab


class GpSansGui(SansGui):
    """GPSANS GUI application."""

    def __init__(self) -> None:
        super().__init__(config_class=SharedConfig)  # type: ignore[arg-type]

    def create_ui(self, *args: Any) -> VAppLayout:
        self.state.trame__title = "GP-SANS Data Reduction"
        with super().create_ui(UserInputTab, StaffInputTab) as layout:
            layout.toolbar_title.set_text("GP-SANS Data Reduction")

            return layout
