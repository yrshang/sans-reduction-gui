"""User Input tab for GP-SANS UI."""

from nova.trame.view.components import InputField, RemoteFileInput
from nova.trame.view.layouts import GridLayout, VBoxLayout
from trame.widgets import vuetify3 as vuetify
from trame_server.core import Server

from common.view_models.config import ConfigViewModel
from common.view_models.oncat import ONCatViewModel
from common.views.trame_components.base import NumberRange
from common.views.trame_components.errors import ErrorNotification
from common.views.trame_components.oncat import PreviewableRunNumber, SampleSelect


class SampleTable:
    """Sample selection widget."""

    def __init__(self) -> None:
        self.create_ui()

    def create_ui(self) -> None:
        with VBoxLayout(stretch=True):
            with vuetify.VOverlay(
                v_if="oncat.updating || oncat.error",
                classes="align-center justify-center",
                contained=True,
                model_value=True,
            ):
                vuetify.VProgressCircular(v_if="!oncat.error", indeterminate=True, size=24)

            with GridLayout(columns=4, classes="mb-1", gap="0.25em"):
                SampleSelect(v_model="config.ranges[index].background_sample")
                SampleSelect(v_model="config.ranges[index].beam_center_sample")
                SampleSelect(v_model="config.ranges[index].empty_beam_sample")
                SampleSelect(v_model="config.ranges[index].block_beam_sample")

            with VBoxLayout():
                InputField(
                    v_model="oncat.sample_search",
                    disabled=("oncat.available_sample_items.length === 0",),
                    label="Search",
                )

            with VBoxLayout(classes="overflow-y-auto", stretch=True):
                with vuetify.VDataTable(
                    v_model="config.ranges[index].samples",
                    classes="overflow-y-auto",
                    headers=("oncat.available_sample_headers",),
                    items=("oncat.available_sample_items",),
                    item_value="name",
                    items_per_page=50,
                    search=("oncat.sample_search",),
                    select_strategy="all",
                    show_select=True,
                    style="max-height: 400px;",
                    update_modelValue="trigger('select_samples', [config.ranges[index].samples, index]);",
                ):
                    for key in ["runs", "transmission"]:
                        with vuetify.Template(raw_attrs=[f"v-slot:item.{key}='{{ item }}'"]):
                            PreviewableRunNumber(key)


class UserInputTab:
    """User Input tab."""

    def __init__(self, server: Server, config_view_model: ConfigViewModel, oncat_view_model: ONCatViewModel) -> None:
        self.ctrl = server.controller
        self.config_vm = config_view_model
        self.oncat_vm = oncat_view_model
        self.oncat_vm.update_experiments()

        self.create_ui()

    def delete_range(self) -> None:
        self.config_vm.delete_range()

    def add_range(self) -> None:
        self.config_vm.add_range()

    def create_ui(self) -> None:
        @self.ctrl.trigger("get_run_number")
        def _get_run_number(run_number: str) -> None:
            if run_number:
                self.oncat_vm.get_run_number(run_number)

        # This handles an event triggered by a data table that isn't an InputField, so we need to handle the event
        # manually.
        @self.ctrl.trigger("select_samples")
        def _select_samples(samples: list[str], qrange: str) -> None:
            self.oncat_vm.update_selected_samples(samples, int(qrange))
            self.config_vm.update_view()
            self.config_vm.gui_config_updated()

        ErrorNotification(
            "oncat.error",
            "ONCat failed to connect, so this tab can't populate the experiment or sample lists. You can still "
            "run a reduction workflow, but you will need to configure it by either uploading a configuration "
            "file or using the advanced settings tab.",
            self.oncat_vm.clear_error,
        )

        with GridLayout(columns=2, classes="mb-2", gap="0.25em"):
            InputField(
                v_model="config.ipts_number",
                disabled=("oncat.updating",),
                items=("oncat.available_experiments",),
                type="autocomplete",
            )
            RemoteFileInput(
                v_model="config.output_folder", allow_files=False, allow_folders=True, base_paths=["/HFIR", "/SNS"]
            )

        with GridLayout(columns=2, classes="mb-2 pb-1", gap="0.25em"):
            with vuetify.VCard(v_for="(range, index) in config.ranges", classes="border-sm", elevation=0):
                vuetify.VCardTitle("Q-range {{ index + 1}}")
                vuetify.VBtn(
                    v_if="index === config.ranges.length - 1 && config.can_remove_range",
                    color="error",
                    icon="mdi-close",
                    position="absolute",
                    size="x-small",
                    style={
                        "right": "1em",
                        "top": "1em",
                    },
                    click=self.delete_range,
                )

                SampleTable()

            with VBoxLayout(halign="center", valign="center"):
                vuetify.VCard(
                    v_if="config.can_add_range",
                    prepend_icon="mdi-plus-circle-outline",
                    title="Add a Q-range",
                    width="fit-content",
                    click=self.add_range,
                )

        with GridLayout(columns=2, gap="0.25em"):
            with VBoxLayout(v_for="(_, index) in config.ranges.length - 1"):
                NumberRange(
                    ["config.stitching[index].min", "config.stitching[index].max"],
                    [
                        ("`Stitching Range Q${index + 1}-Q${index + 2}: Start`",),
                        ("`Stitching Range Q${index + 1}-Q${index + 2}: End`",),
                    ],
                )
