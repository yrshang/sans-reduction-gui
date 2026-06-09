"""Job outputs tab."""

from nova.trame.view.components import InputField
from nova.trame.view.layouts import HBoxLayout, VBoxLayout
from trame.widgets import client
from trame.widgets import vuetify3 as vuetify
from trame_client.widgets import html

from common.view_models.job_outputs import JobOutputsViewModel


class JobOutputsTab:
    """Job outputs tab."""

    def __init__(self, viewmodel: JobOutputsViewModel) -> None:
        self.view_model = viewmodel
        self.view_model.job_output_bind.connect("job")
        self.view_model.scroll_position_bind.connect("scroll_positions")
        self.view_model.scroll_bind.connect(
            client.JSEval(
                exec=(
                    "let el = window.document.querySelector(`#${$event}`); "
                    "el !== null && el.scrollTop === scroll_positions[$event] "
                    "  ? (el.scrollTop = el.scrollHeight, scroll_positions[$event] = el.scrollTop) "
                    "  : scroll_positions[$event] = el !== null && el.scrollTop === el.scrollHeight - el.clientHeight ?"
                    " el.scrollTop : null "
                )
            ).exec
        )
        self.view_model.update_view()
        self.create_ui()

    def create_ui(self) -> None:
        with vuetify.VProgressLinear(
            height="25",
            model_value=("job.progress", "0"),
            striped=True,
            v_show=("job.show_progress",),
        ):
            html.H5(v_text="job.state_details")
        with vuetify.VProgressLinear(
            height="25",
            model_value="100",
            striped=False,
            color="error",
            v_show=("job.show_failed",),
        ):
            html.H5(v_text="job.state_details", classes="text-white")
        with vuetify.VProgressLinear(
            height="25",
            model_value="100",
            striped=False,
            color="primary",
            v_show=("job.show_ok",),
        ):
            html.H5(v_text="job.state_details", classes="text-white")

        with HBoxLayout(gap="0.25em", stretch=True):
            with client.DeepReactive("view_state"):
                with vuetify.VTabs(v_model="view_state.active_output_tab", direction="vertical"):
                    vuetify.VTab("Console output", value=1)
                    vuetify.VTab("Console error", value=2)

            with VBoxLayout(v_show="view_state.active_output_tab == 1", stretch=True):
                InputField(v_model="job.output", id="job-outputs", no_resize=True, readonly=True, type="autoscroll")
            with VBoxLayout(v_show="view_state.active_output_tab == 2", stretch=True):
                InputField(v_model="job.error", id="job-errors", no_resize=True, readonly=True, type="autoscroll")
