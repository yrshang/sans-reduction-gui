"""Stitching tab."""

from typing import Any

from nova.trame.view.components import InputField
from nova.trame.view.layouts import GridLayout
from trame.widgets import client, html, vega
from trame.widgets import vuetify3 as vuetify

from common.view_models.stitching import StitchingViewModel
from common.views.trame_components.base import NumberRange


class StitchingTab:
    """Stitching tab."""

    def __init__(self, server: Any, viewmodel: StitchingViewModel) -> None:
        self.ctrl = server.controller
        self.state = server.state

        self.view_model = viewmodel
        # Front-end charts will be fully replaced on update, and this will re-register callbacks.
        self.view_model.prepare_charts_bind.connect(client.JSEval(exec="window.prepare_charts();").exec)
        self.view_model.available_stitching_profiles_bind.connect("available_profiles")
        self.view_model.export_error_bind.connect("export_error")
        self.view_model.exporting_bind.connect("exporting_stitching_result")
        self.view_model.log_axes_bind.connect("log_axes")
        self.view_model.needs_export_bind.connect("needs_export")
        self.view_model.plots_1D_bind.connect("plots_1D")
        self.view_model.stitching_profiles_bind.connect("stitching_profiles")
        self.view_model.stitching_error_bind.connect("stitching_error")
        self.view_model.stitching_in_progress_bind.connect("stitching_in_progress")

        self.view_model.update_view()

        self.create_ui()

    def add_stitching_profile(self) -> None:
        self.view_model.add_stitching_profile()

    def delete_stitching_profile(self, index: int) -> None:
        self.view_model.delete_stitching_profile(index)

    def export_stitched_profile(self) -> None:
        self.view_model.export_stitched_profile()

    def create_ui(self) -> None:
        @self.ctrl.trigger("stitch")
        def on_stitch() -> None:
            self.state.flush()
            self.view_model.stitch()

        @self.ctrl.trigger("update_log_axes")
        def on_update_log_axes(index: int, axis: Any, value: Any) -> None:
            self.view_model.update_log_axes(index, axis, value)

        @self.ctrl.trigger("update_stitching_profile")
        def on_update_stitching_profile(index: int, value: Any) -> None:
            self.view_model.update_stitching_profile(index, value)

        @self.ctrl.trigger("interval_selection")
        def on_interval_selection(index: int, interval: Any) -> None:
            self.view_model.update_overlap(index, interval)

        with vuetify.VOverlay(
            v_model="stitching_in_progress",
            classes="align-center d-flex justify-center",
        ):
            vuetify.VProgressCircular(indeterminate=True, size=64)

        InputField(v_model="config.stitching_sample", items=("config.sample_names",), type="autocomplete")

        with GridLayout(
            v_if=("plots_1D.length > 0",),
            classes="mb-2",
            columns=2,
            fluid=True,
            id="overlap_plots",
        ):
            for index in range(self.view_model.get_max_ranges() - 1):
                with vuetify.VCard(v_if=f"plots_1D.length > {index + 1}", classes="position-relative"):
                    vuetify.VBtn(
                        color="error",
                        icon="mdi-close",
                        position="absolute",
                        size="x-small",
                        style={
                            "right": "1em",
                            "top": "1em",
                        },
                        click=(self.delete_stitching_profile, f"[{index}]"),
                    )

                    vuetify.VCardTitle(f"Overlap {index + 1}", classes="text-center")

                    with GridLayout(columns=2, dense=True, fluid=True):
                        # These can't use InputField due to the config validation behavior it provides.
                        vuetify.VSelect(
                            v_model=f"stitching_profiles[{index}]",
                            items=("available_profiles",),
                            update_modelValue=f"trigger('update_stitching_profile', [{index}, $event])",
                        )
                        vuetify.VSelect(
                            v_model=f"stitching_profiles[{index + 1}]",
                            items=("available_profiles",),
                            update_modelValue=f"trigger('update_stitching_profile', [{index + 1}, $event])",
                        )

                        self.view_model.add_figure(
                            vega.Figure(
                                ref=f"stitching_{index}",
                                column_span=2,
                                figure=None,
                                style={"height": "450px", "width": "100%"},
                            )
                        )

                        with html.Div(classes="d-flex", column_span=2):
                            InputField(
                                v_model=f"log_axes[{index}][0]",
                                classes="flex-1-0",
                                label="Log X",
                                type="checkbox",
                                update_modelValue=f"trigger('update_log_axes', [{index}, 0, $event])",
                            )
                            InputField(
                                v_model=f"log_axes[{index}][1]",
                                classes="flex-1-0",
                                label="Log Y",
                                type="checkbox",
                                update_modelValue=f"trigger('update_log_axes', [{index}, 1, $event])",
                            )
                            NumberRange(
                                ["config.stitching[index].min", "config.stitching[index].max"],
                                [
                                    (f"`Stitching Range {index + 1}: Q${{ stitching_profiles[{index}] + 1 }}`",),
                                    (f"`Stitching Range {index + 1}: Q${{ stitching_profiles[{index + 1}] + 1 }}`",),
                                ],
                                v_if=f"config.stitching.length > {index}",
                                v_for=f"index in [{index}]",
                                __events=["change"],
                                change="window.setTimeout(() => { trigger('stitch'); }, 100)",
                            )

            with html.Div(
                v_if="stitching_profiles.length < config.ranges.length",
                classes="align-center d-flex h-100 justify-center w-100",
            ):
                vuetify.VCard(
                    prepend_icon="mdi-plus-circle-outline",
                    title="Add a new overlap",
                    width="fit-content",
                    click=self.add_stitching_profile,
                )

        with html.Div(
            v_if="plots_1D.length > 0",
            classes=("`align-center d-flex flex-column ${stitching_error ? 'border-error' : ''}`",),
        ):
            vuetify.VAlert(
                v_if="stitching_error",
                classes="mb-4",
                color="error",
                text=("`Error stitching profiles: ${stitching_error}`",),
                type="error",
            )

            self.view_model.add_figure(
                vega.Figure(
                    ref=f"stitching_{self.view_model.get_max_ranges() - 1}",
                    classes="w-50",
                    figure=None,
                    style={"height": "450px"},
                )
            )

            with html.Div(classes="d-flex"):
                InputField(
                    v_model="log_axes[log_axes.length - 1][0]",
                    label="Log X",
                    type="checkbox",
                    update_modelValue="trigger('update_log_axes', [-1, 0, $event])",
                )
                InputField(
                    v_model="log_axes[log_axes.length - 1][1]",
                    label="Log Y",
                    type="checkbox",
                    update_modelValue="trigger('update_log_axes', [-1, 1, $event])",
                )
            with html.Div(classes="mb-1 text-center"):
                vuetify.VAlert(
                    v_if="export_error",
                    classes="mb-4",
                    color="error",
                    text=("`Export error: ${export_error}`",),
                    type="error",
                )
                vuetify.VBtn(
                    "{{ needs_export ? 'Export to Analysis Cluster' : 'Exported to Analysis Cluster' }}",
                    classes="mb-2",
                    disabled=("!needs_export || exporting_stitching_result",),
                    loading=("exporting_stitching_result",),
                    prepend_icon=("needs_export ? 'mdi-export' : 'mdi-check'",),
                    click=self.export_stitched_profile,
                )
