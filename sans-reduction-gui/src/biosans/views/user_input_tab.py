"""User Input tab for BioSANS UI."""

from nova.trame.view.components import InputField, RemoteFileInput
from nova.trame.view.layouts import GridLayout, VBoxLayout
from trame.widgets import vuetify3 as vuetify
from trame_server.core import Server

from common.view_models.config import ConfigViewModel
from common.view_models.oncat import ONCatViewModel
from common.views.trame_components.errors import ErrorNotification
from common.views.trame_components.oncat import PreviewableRunNumber, SampleSelect


class UserInputTab:
    """User Input tab."""

    def __init__(self, server: Server, config_view_model: ConfigViewModel, oncat_view_model: ONCatViewModel) -> None:
        self.ctrl = server.controller
        self.config_vm = config_view_model
        self.oncat_vm = oncat_view_model
        self.oncat_vm.update_experiments()

        self.create_ui()

    def create_ui(self) -> None:
        @self.ctrl.trigger("get_run_number")
        def _get_run_number(run_number: str) -> None:
            if run_number:
                self.oncat_vm.get_run_number(run_number)

        # This handles an event triggered by a data table that isn't an InputField, so we need to handle the event
        # manually.
        @self.ctrl.trigger("select_samples")
        def _select_samples(samples: list[str]) -> None:
            self.oncat_vm.update_selected_samples(samples)
            self.config_vm.update_view()

        ErrorNotification(
            "oncat.error",
            "ONCat failed to connect, so this tab can't populate the experiment or sample lists. You can still "
            "run a reduction workflow, but you will need to configure it by either uploading a configuration "
            "file or using the advanced settings tab.",
            self.oncat_vm.clear_error,
        )

        with GridLayout(columns=2, gap="0.25em"):
            InputField(
                v_model="config.ipts_number",
                disabled=("oncat.updating",),
                items=("oncat.available_experiments",),
                type="autocomplete",
            )
            RemoteFileInput(
                v_model="config.output_folder", allow_files=False, allow_folders=True, base_paths=["/HFIR", "/SNS"]
            )

        with VBoxLayout(classes="position-relative", stretch=True):
            with vuetify.VOverlay(
                v_if="oncat.updating || oncat.error",
                classes="align-center justify-center",
                contained=True,
                model_value=True,
            ):
                vuetify.VProgressCircular(v_if="!oncat.error", indeterminate=True, size=24)

            with GridLayout(columns=3, gap="0.25em"):
                SampleSelect(v_model="config.background_sample")
                SampleSelect(v_model="config.beam_center_sample")
                SampleSelect(v_model="config.empty_beam_sample")

            with VBoxLayout():
                InputField(
                    v_model="oncat.sample_search",
                    disabled=("oncat.available_sample_items.length === 0",),
                    label="Search",
                )

            with VBoxLayout(classes="overflow-y-auto", stretch=True):
                with vuetify.VDataTable(
                    v_model="config.sample_names",
                    classes="h-100",
                    headers=("oncat.available_sample_headers",),
                    items=("oncat.available_sample_items",),
                    item_value="name",
                    items_per_page=50,
                    search=("oncat.sample_search",),
                    select_strategy="all",
                    show_select=True,
                    update_modelValue="trigger('select_samples', [config.sample_names]);",
                ):
                    for key in ["runs", "transmission"]:
                        with vuetify.Template(raw_attrs=[f"v-slot:item.{key}='{{ item }}'"]):
                            PreviewableRunNumber(key)
