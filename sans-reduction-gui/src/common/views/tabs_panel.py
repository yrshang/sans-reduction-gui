"""Defines the v-tabs component at the top of the application."""

from typing import Any

from trame.widgets import client
from trame.widgets import vuetify3 as vuetify


class TabsPanel:
    """Tabs Panel."""

    def __init__(self, server: Any, view_models: Any, user_input_tab: Any = None, staff_input_tab: Any = None) -> None:
        self.stitching_view_model = view_models["stitching"]
        self.create_ui(user_input_tab, staff_input_tab)

    def create_ui(self, user_input_tab: Any = None, staff_input_tab: Any = None) -> None:
        with client.DeepReactive("view_state"):
            with vuetify.VTabs(v_model="view_state.active_tab", classes="pl-5"):
                if user_input_tab:
                    vuetify.VTab("User Input", value=1, disabled=("config_tab_disabled",))
                if staff_input_tab:
                    vuetify.VTab("Instrument Input", value=2, disabled=("config_tab_disabled",))
                vuetify.VTab("Advanced Settings", value=3, disabled=("config_tab_disabled",))
                vuetify.VTab("Job Execution", value=4)
                vuetify.VTab("Job Results", value=5, disabled=("results_tab_disabled",))
                vuetify.VTab(
                    "Stitching",
                    value=6,
                    disabled=("results_tab_disabled",),
                    click=self.stitching_view_model.update_view,
                )
