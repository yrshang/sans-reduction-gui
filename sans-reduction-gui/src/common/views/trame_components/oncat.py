"""Trame components for the ONCat integration."""

from typing import Any, Optional, Union

from nova.trame.view.components import InputField
from nova.trame.view.layouts import GridLayout
from trame.widgets import client, html, plotly
from trame.widgets import vuetify3 as vuetify


class PreviewableRunNumber:
    """Displays a run number and shows a dialog with data previews on hover."""

    def __init__(self, key: str) -> None:
        with html.Span(
            f"{{{{ item.{key}.length > 3"
            f"  ? `${{item.{key}.length}} runs` "
            f"  : item.{key}.map((run) => run.run_number).join(', ') }}}}"
        ):
            with vuetify.VMenu(
                v_if=f"item.{key}.length > 0",
                activator="parent",
                close_on_content_click=False,
                open_on_hover=True,
                width=700,
            ):
                with vuetify.VCard():
                    client.ClientTriggers(mounted=f"trigger('get_previews', [item.{key}])")
                    vuetify.VCardTitle("Runs")

                    with GridLayout(columns=2):
                        with html.Div(
                            v_for=f"run in item.{key}",
                            classes="align-center d-flex flex-column",
                        ):
                            vuetify.VCardSubtitle(
                                "{{ run.run_number }} - {{ run.title }}",
                            )
                            plotly.Figure(
                                v_if="oncat.previews[run.run_number]?.heatmap",
                                display_mode_bar=("false",),
                                state_variable_name="oncat.previews[run.run_number]?.heatmap",
                                style={
                                    "height": "300px",
                                    "width": "300px",
                                },
                            )
                            html.P(
                                "Could not preview {{ run.location }}: {{ oncat.previews[run.run_number].error }}.",
                                v_else_if="oncat.previews[run.run_number]?.error",
                                classes="text-caption",
                            )
                            vuetify.VProgressCircular(v_else=True, indeterminate=True)


class SampleSelect:
    """VSelect that connects to ONCat to search for run numbers outside of the selected IPTS."""

    def __init__(self, v_model: Optional[Union[tuple[str, Any], str]] = None) -> None:
        # custom_filter checks to see if the user query is contained within the sample name or any of the run numbers
        # associated with the sample.
        # update_search searches for the user query in ONCat with a debounce to avoid overloading ONCat.
        InputField(
            v_model=v_model,
            custom_filter=(
                (
                    "(_, query, item) => {"
                    "  return item.title.toLowerCase().includes(query.toLowerCase()) ||"
                    "    ("
                    "      item.raw !== undefined &&"
                    "      (item.raw.runs.some((run) => run.run_number.toString().includes(query)) ||"
                    "      item.raw.transmission.some((trans) => trans.run_number.toString().includes(query)))"
                    "    );"
                    "}"
                ),
            ),
            disabled=("oncat.available_sample_items.length === 0",),
            items=("oncat.search_items",),
            item_title="name",
            return_object=True,
            type="autocomplete",
            update_search=(
                "window.delay_manager.debounce("
                "  'config.background_sample',"
                "  (value) => { trigger('get_run_number', [value]); },"
                "  250,"
                "  $event"
                ");"
            ),
        )
