"""Defines the v-main contents for the application."""

from typing import Any

from nova.trame.view.layouts import VBoxLayout
from trame.widgets import client
from trame_server.core import Server

from common.views.advanced_settings_tab import AdvancedSettingsTab
from common.views.job_outputs_tab import JobOutputsTab
from common.views.job_results_tab import JobResultsTab
from common.views.stitching_tab import StitchingTab


class TabContentPanel:
    """Tab content panel."""

    def __init__(
        self, server: Server, view_models: dict[str, Any], user_input_tab: Any = None, staff_input_tab: Any = None
    ) -> None:
        self.ctrl = server.controller
        self.config_view_model = view_models["config"]
        self.oncat_view_model = view_models["oncat"]
        self.oncat_view_model.view_state_bind.connect("oncat")
        self.job_results_view_model = view_models["job_results"]
        self.job_outputs_view_model = view_models["job_outputs"]
        self.stitching_view_model = view_models["stitching"]
        self.server = server
        self.ctrl = server.controller
        self.ctrl.on_server_ready.add(self.server_ready)
        self.config_view_model.view_state_bind.connect("view_state")
        self.config_view_model.gui_config_bind.connect("config")
        self.config_view_model.tab_state_bind.connect()
        self.create_ui(user_input_tab, staff_input_tab)
        self.val = client.JSEval(exec="trame.refs.form.validate()").exec

    def server_ready(self, **_kwargs: Any) -> None:
        self.config_view_model.gui_config_updated()
        self.config_view_model.update_view()

    def validate_form(self, _value: Any) -> None:
        self.val()

    def create_ui(self, user_input_tab: Any = None, staff_input_tab: Any = None) -> None:
        if user_input_tab:
            with VBoxLayout(v_show="view_state.active_tab == 1", stretch=True):
                user_input_tab(
                    self.server,
                    self.config_view_model,
                    self.oncat_view_model,
                )
        if staff_input_tab:
            with VBoxLayout(v_show="view_state.active_tab == 2", stretch=True):
                staff_input_tab(self.config_view_model)
        with VBoxLayout(v_show="view_state.active_tab == 3", stretch=True):
            AdvancedSettingsTab(self.server, self.config_view_model)
        with VBoxLayout(v_show="view_state.active_tab == 4", stretch=True):
            JobOutputsTab(self.job_outputs_view_model)
        with VBoxLayout(v_if="view_state.active_tab == 5", stretch=True):
            JobResultsTab(self.server, self.job_results_view_model)
        with VBoxLayout(v_show="view_state.active_tab == 6", stretch=True):
            StitchingTab(self.server, self.stitching_view_model)

        @self.ctrl.trigger("get_previews")
        def get_previews(runs: list[dict[str, Any]]) -> None:
            self.oncat_view_model.get_previews(runs)
