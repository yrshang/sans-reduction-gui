"""Staff input tab."""

from nova.trame.view.components import InputField
from nova.trame.view.layouts import GridLayout, HBoxLayout
from trame.widgets import html
from trame.widgets import vuetify3 as vuetify

from common.view_models.config import ConfigViewModel
from common.views.trame_components.base import NumberRange


class StaffInputTab:
    """Staff input tab."""

    def __init__(self, viewmodel: ConfigViewModel) -> None:
        self.view_model = viewmodel
        self.create_ui()

    def create_ui(self) -> None:
        with GridLayout(columns=2, gap="0.25em"):
            with vuetify.VCard(v_for="(range, index) in config.ranges", classes="border-sm", elevation=0):
                vuetify.VCardTitle("Q-range {{ index + 1 }} Masks and Dark Scan")

                with HBoxLayout(gap="0.25em"):
                    InputField(v_model="config.ranges[index].use_mask_file", type="checkbox")
                    InputField(
                        v_model="config.ranges[index].mask_file_name",
                        disabled=("!range.use_mask_file", False),
                        column_span=2,
                    )

                with HBoxLayout(gap="0.25em"):
                    InputField(v_model="config.ranges[index].use_dark_file", type="checkbox")
                    InputField(
                        v_model="config.ranges[index].dark_file_name",
                        disabled=("!range.use_dark_file", False),
                        column_span=2,
                    )

                with HBoxLayout(gap="0.25em"):
                    InputField(v_model="config.ranges[index].use_mask_back_tubes", type="checkbox")
                    InputField(v_model="config.ranges[index].wavelength")
                    InputField(v_model="config.ranges[index].wavelength_spread")

        with GridLayout(classes="pa-1", columns=2):
            with html.Div(v_for="(_, index) in config.ranges.length"):
                NumberRange(
                    ["config.q_range_clean_curves[index].min", "config.q_range_clean_curves[index].max"],
                    [
                        ("`Q-range ${ index+1 } to clean 1D curve: Start`",),
                        ("`Q-range ${ index+1 } to clean 1D curve: End`",),
                    ],
                )

        with HBoxLayout(gap="0.25em"):
            InputField(v_model="config.see_full_verbose", type="checkbox")
            InputField(v_model="config.use_log_2d_binning", type="checkbox")
