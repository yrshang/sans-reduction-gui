"""Defines the top-level BioSANS GUI."""

from typing import Any

from trame.ui.vuetify3 import VAppLayout

from biosans.models.config import SharedConfig
from biosans.views.staff_input_tab import StaffInputTab
from biosans.views.user_input_tab import UserInputTab
from common.views.main import SansGui


class BioSansGui(SansGui):
    """BioSANS GUI application."""

    def __init__(self) -> None:
        super().__init__(config_class=SharedConfig)  # type: ignore[arg-type]

    def create_ui(self, *args: Any) -> VAppLayout:
        self.state.trame__title = "Bio-SANS Data Reduction"
        with super().create_ui(UserInputTab, StaffInputTab) as layout:
            layout.toolbar_title.set_text("Bio-SANS Data Reduction")

            return layout
