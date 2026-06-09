"""Top level of the stitching view model."""

import asyncio
import logging
import threading
from typing import Any, List, Optional, Union

import altair
import numpy as np
import pandas
from nova.common.events import get_event
from nova.mvvm.interface import BindingInterface

from common.models.config import StitchingRange
from common.models.main import MainModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class StitchingViewModel:
    """Stitching view model."""

    def __init__(self, model: MainModel, binding: BindingInterface) -> None:
        self.model = model
        self.export_error = ""
        self.exporting = False
        self.figures: List[Any] = [None] * model.config.MAX_RANGES_NUM
        self.needs_export = False
        self.stitching_error: Union[bool, str] = ""

        self.prepare_charts_bind = binding.new_bind()
        self.validation_bind = binding.new_bind()

        self.available_stitching_profiles_bind = binding.new_bind()
        self.export_error_bind = binding.new_bind()
        self.exporting_bind = binding.new_bind()
        self.needs_export_bind = binding.new_bind()
        self.log_axes_bind = binding.new_bind()
        self.plots_1D_bind = binding.new_bind()
        self.stitching_error_bind = binding.new_bind()
        self.stitching_profiles_bind = binding.new_bind()
        self.stitching_in_progress_bind = binding.new_bind()

    def update_view(self) -> None:
        job_results = self.model.get_job_results()
        self.model.update_1d_plots(self.model.config.stitching_sample, job_results)

        self.available_stitching_profiles_bind.update_in_view(self.model.get_available_stitching_profiles())
        self.export_error_bind.update_in_view(self.export_error)
        self.exporting_bind.update_in_view(self.exporting)
        self.needs_export_bind.update_in_view(self.needs_export)
        self.stitching_profiles_bind.update_in_view(self.model.get_stitching_profiles())
        self.stitching_error_bind.update_in_view(self.stitching_error)

        log_axes = self.model.get_log_axes()
        plots = self.model.get_1d_plots()
        self.log_axes_bind.update_in_view(log_axes)
        self.plots_1D_bind.update_in_view(plots)
        for index, _ in enumerate(plots[:-1]):
            if index >= len(self.figures) - 1 or self.figures[index] is None:
                continue
            self.figures[index].update(
                self.render_1d_plot(
                    plots[index],
                    log_axes[index],
                    self.model.config.stitching[index],
                    False,
                )
            )
        if plots and self.figures:
            # The merged profile should always be the last figure needs to always be the final figure in
            # order to handle profile deletion and addition properly.
            self.figures[-1].update(self.render_1d_plot(plots[-1], log_axes[-1], None, True))

        self.prepare_charts_bind.update_in_view(None)

    def add_figure(self, figure: Any) -> None:
        try:
            self.figures[self.figures.index(None)] = figure
        except ValueError:
            self.figures.append(figure)

    def add_stitching_profile(self) -> None:
        self.model.add_stitching_profile()
        self.stitch()

    def update_stitching_profile(self, index: int, value: Any) -> None:
        self.model.update_stitching_profile(index, value)
        self.stitch()

    def delete_stitching_profile(self, index: int) -> None:
        self.model.delete_stitching_profile(index)
        self.stitch()

    def render_1d_plot(
        self, data: Any, logscale: List[Any], stitching_values: Optional[StitchingRange], merged: bool = False
    ) -> Any:
        chart = altair.Chart(pandas.DataFrame(data)).transform_calculate(
            ymin="datum.y - datum.error", ymax="datum.y + datum.error"
        )

        # Vega's symlog scale handles positive and negative values in the same domain, but it requires an extra constant
        # to be set that determines a domain near zero at which the scale should be linear. The default is 1, which
        # produces poor results in most cases. The matplotlib equivalent recommends setting this to the closest value to
        # zero.
        if logscale[0]:
            x_symlog_constant = np.min(np.abs([x for x in data["x"] if x != 0.0]))
            x_scale = {"type": "symlog", "constant": x_symlog_constant, "zero": False}
        else:
            x_scale = {"type": "linear", "zero": False}

        if logscale[1]:
            y_symlog_constant = np.min(np.abs([y for y in data["y"] if y != 0.0]))
            y_scale = {"type": "symlog", "constant": y_symlog_constant, "zero": False}
        else:
            y_scale = {"type": "linear", "zero": False}

        lines = chart.mark_line(point=True).encode(
            x={"field": "x", "scale": x_scale, "title": "Q"},
            y={"field": "y", "scale": y_scale, "title": "Intensity"},
            color={"field": "profile", "title": "Profile"},
            order={"field": "x"},
            tooltip=["x", "y", "profile"],
        )

        errorbars = chart.mark_errorbar(ticks=True).encode(
            x="x",
            y={"field": "ymin", "title": "Intensity", "type": "quantitative"},
            y2="ymax:Q",
            color="profile",
        )

        cursor = "ew-resize" if not merged else "default"

        layer_chart = lines + errorbars
        layer_chart = layer_chart.configure_view(cursor=cursor).properties(
            autosize=altair.AutoSizeParams(contains="padding", type="fit"),
            height=450,
            title="Merged Profile" if merged else "",
            width="container",
        )

        if merged:
            return layer_chart
        else:
            if stitching_values:
                for index, value in enumerate(stitching_values):
                    if value is None:
                        stitching_values[index] = 0.0

            selection = altair.selection_interval(
                encodings=["x"],
                mark=altair.BrushConfig(cursor="move", fill="red"),  # type: ignore[arg-type]
                name="select",
                value=({"x": [stitching_values.min, stitching_values.max]} if stitching_values else None),
                zoom=False,
            )

            return layer_chart.add_params(selection)

    def update_log_axes(self, index: int, axis: int, value: Any) -> None:
        self.model.update_log_axes(index, axis, value)
        self.update_view()

    def update_overlap(self, index: int, interval: Any) -> None:
        try:
            self.model.update_overlap(index, interval)
            get_event("config-update").send_sync()
            self.stitch()
        except Exception as e:
            logger.error(f"Error during overlap update: {e}")
            self.stitching_in_progress_bind.update_in_view(False)

    def stitch(self) -> None:
        result = self.model.stitch()
        if result is True:
            self.needs_export = True
            self.stitching_error = ""
        elif result is not None:
            self.needs_export = False
            self.stitching_error = result

        self.update_view()

    def export_in_background(self) -> None:
        result = self.model.export_stitched_profile()

        self.exporting = False
        if result:
            if result["success"]:
                self.export_error = ""
                self.needs_export = False
            else:
                self.export_error = result["error"]
                self.needs_export = True

    def export_stitched_profile(self) -> None:
        if not self.exporting:
            self.exporting = True
            self.exporting_bind.update_in_view(self.exporting)

            # This is not an immediate operation, and I don't want to block the UI event loop waiting on it to finish.
            self.export_thread = threading.Thread(target=self.export_in_background)
            self.export_thread.daemon = True
            self.export_thread.start()
            asyncio.create_task(self.monitor_export())

    async def monitor_export(self) -> None:
        while self.exporting:
            await asyncio.sleep(0.1)
        self.update_view()

    def get_max_ranges(self) -> int:
        return self.model.get_max_ranges()

    def set_default_sample(self) -> None:
        if not self.model.config.stitching_sample and self.model.config.sample_names:
            self.model.config.stitching_sample = self.model.config.sample_names[0]
