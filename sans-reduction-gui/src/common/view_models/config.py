"""Config view model."""

import copy
import logging
import re
import types
from functools import partial
from typing import Any, Dict, List, Optional, Union

from nova.common.events import get_event
from nova.mvvm.interface import BindingInterface
from pydantic import BaseModel, Field

from common.models.job import job_states
from common.view_models.stitching import StitchingViewModel

tabs = types.SimpleNamespace()

tabs.USER_INPUT = "1"
tabs.INSTRUMENT_INPUT = "2"
tabs.ADVANCED_SETTINGS = "3"
tabs.JOB_EXECUTION = "4"
tabs.JOB_RESULTS = "5"
tabs.STITCHING = "6"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ViewState(BaseModel):
    """Pydantic model for holding validation errors."""

    active_tab: str = Field(default="1")
    active_output_tab: str = Field(default="1")
    errors: List[str] = Field(default=[])


class ConfigViewModel:
    """Config View Model."""

    def __init__(
        self,
        model: Any,
        oncat_vm: Any,
        stitching_vm: StitchingViewModel,
        binding: BindingInterface,
    ) -> None:
        self.binding = binding

        self.view_state = ViewState()
        self.model = model
        self.oncat_vm = oncat_vm
        self.stitching_vm = stitching_vm
        self.config_tab_disabled = False
        self.results_tab_disabled = True
        self.text_config = ""
        self.gui_config_bind = binding.new_bind(self.model.config, callback_after_update=self.gui_config_updated)
        self.text_config_bind = binding.new_bind(self, ["text_config"])
        self.view_state_bind = binding.new_bind(self.view_state)

        self.tab_state_bind = binding.new_bind(self, ["config_tab_disabled", "results_tab_disabled"])

        get_event("config-update").connect(lambda *args: self.update_view())

    def gui_config_updated(self, results: Optional[dict[str, Any]] = None) -> None:
        if results:
            self.process_errors(results.get("errored", []))
            self.process_updates(results.get("updated", []))

        try:
            new_text_config = self.model.prepare_config_file()
        except Exception as err:
            logger.error(err)
            new_text_config = "Current config is invalid"
        if new_text_config != self.text_config:
            self.text_config = new_text_config
            self.text_config_bind.update_in_view(self)
            self.stitching_vm.update_view()

    def text_config_updated(self) -> None:
        try:
            old_ipts_number = self.model.config.ipts_number
            old_text_config = self.model.prepare_config_file()
        except Exception:
            old_text_config = None
        if old_text_config != self.text_config and self.validate_text_config(self.text_config) is True:
            self.model.load_config(self.text_config)
            self.stitching_vm.update_view()

            if self.model.config.ipts_number != old_ipts_number:
                self.update_oncat()

            self.gui_config_bind.update_in_view(self.model.config)
            self.update_view()

    def update_oncat(self) -> None:
        self.oncat_vm.set_updating(True)

        worker = self.binding.new_worker(partial(self.oncat_vm.update_samples, self.model.config.ipts_number))
        worker.connect_finished(self.oncat_vm.update_view)
        worker.connect_result(self.on_oncat_update)
        worker.start()

    def on_oncat_update(self, samples_by_run_number: Dict[int, str]) -> None:
        self.model.update_sample_selections(samples_by_run_number)
        self.gui_config_bind.update_in_view(self.model.config)
        self.update_view()

    def process_errors(self, errors: List[Exception]) -> None:
        self.view_state.errors = []
        for error in errors:
            self.view_state.errors.append(str(error))
        self.view_state_bind.update_in_view(self.view_state)

    def process_updates(self, updates: list[str]) -> None:
        for update in updates:
            # TODO: refactor
            if update.startswith("ranges"):
                try:
                    parsed_text = re.search(r"\[(\d+)\]", update)
                    if parsed_text is not None:
                        index = int(parsed_text.group(1))
                    else:
                        continue

                    if "background_sample" in update:
                        self.update_background(index)
                    elif "beam_center_sample" in update:
                        self.update_beam_center(index)
                    elif "empty_beam_sample" in update:
                        self.update_empty_beam(index)
                    elif "block_beam_sample" in update:
                        self.update_block_beam(index)

                    continue
                except Exception:
                    pass

            match update:
                case "ipts_number":
                    self.update_experiment()
                case "background_sample":
                    self.update_background()
                case "beam_center_sample":
                    self.update_beam_center()
                case "config_type":
                    self.model.config.update_configuration()
                case "empty_beam_sample":
                    self.update_empty_beam()
                case "flexible_pixelsizes":
                    self.model.config.update_configuration()
                case "run_cycle":
                    self.model.config.update_configuration()
                case "sample_env":
                    self.model.config.update_configuration()
                case "stitching_sample":
                    self.stitching_vm.update_view()

        if updates:
            self.update_view()

    def delete_range(self) -> None:
        self.model.config.reduce_n_ranges()
        self.update_view()

    def add_range(self) -> None:
        self.model.config.add_range()
        self.update_view()

    def update_background(self, index: Optional[int] = None) -> None:
        self.model.config.update_background(index)

    def update_beam_center(self, index: Optional[int] = None) -> None:
        self.model.config.update_beam_center(index)

    def update_empty_beam(self, index: Optional[int] = None) -> None:
        self.model.config.update_empty_beam(index)

    def update_block_beam(self, index: Optional[int] = None) -> None:
        self.model.config.update_block_beam(index)

    def update_experiment(self) -> None:
        self.model.config.update_output_folder()

        self.update_oncat()

    def update_view(self) -> None:
        self.view_state_bind.update_in_view(self.view_state)
        self.gui_config_bind.update_in_view(copy.deepcopy(self.model.config))
        job = self.model.get_job()
        if job.state == job_states.RUNNING or (
            job.state != job_states.FINISHED_OK and self.view_state.active_tab == tabs.JOB_RESULTS
        ):
            self.view_state.active_tab = tabs.JOB_EXECUTION
            self.view_state_bind.update_in_view(self.view_state)
        self.config_tab_disabled = job.state == job_states.RUNNING or job.state == job_states.CANCELING
        self.results_tab_disabled = job.state != job_states.FINISHED_OK
        self.tab_state_bind.update_in_view(self)

    def disable_results_pages(self) -> None:
        if self.view_state.active_tab in [tabs.JOB_RESULTS, tabs.STITCHING]:
            self.view_state.active_tab = tabs.USER_INPUT
            self.view_state_bind.update_in_view(self.view_state)
        self.results_tab_disabled = True
        self.tab_state_bind.update_in_view(self)

    def validate_text_config(self, value: str) -> Union[bool, str]:
        try:
            self.model.config.model_validate_json(value)
            self.process_errors([])
        except Exception as err:
            self.process_errors([err])
            return str(err)

        return True
