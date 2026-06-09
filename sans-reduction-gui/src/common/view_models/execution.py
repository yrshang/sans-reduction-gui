"""Execution view model."""

import asyncio
import os
import threading
from typing import Any, Optional

from nova.mvvm.interface import BindingInterface
from pydantic import BaseModel, Field

from common.models.job import job_states
from common.view_models.config import ConfigViewModel
from common.view_models.job_outputs import JobOutputsViewModel
from common.view_models.job_results import JobResultsViewModel
from common.view_models.stitching import StitchingViewModel


def folder_exists_and_not_empty(folder_path: str) -> bool:
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        if os.listdir(folder_path):
            return True
        else:
            return False
    else:
        return False


class ViewState(BaseModel):
    """View state for the execution view model."""

    upload_error: str = Field(default="")
    upload_failed: bool = Field(default=False)


class ExecutionViewModel:
    """Execution view model."""

    def __init__(
        self,
        model: Any,
        outputs_vm: JobOutputsViewModel,
        config_vm: ConfigViewModel,
        results_vm: JobResultsViewModel,
        oncat_vm: Any,
        stitching_vm: StitchingViewModel,
        binding: BindingInterface,
    ) -> None:
        self.model = model
        self.outputs_vm = outputs_vm
        self.config_vm = config_vm
        self.results_vm = results_vm
        self.oncat_vm = oncat_vm
        self.stitching_vm = stitching_vm

        self.view_state = ViewState()
        self.view_state_bind = binding.new_bind(self.view_state)

        self.run_disabled = False
        self.cancel_disabled = True
        self.config_disabled = False
        self.skip_confirmation = False

        self.reset_form_bind = binding.new_bind()
        self.buttons_state_bind = binding.new_bind(
            self, ["run_btn_disabled", "cancel_btn_disabled", "config_btn_disabled"]
        )
        self.galaxy_running_bind = binding.new_bind()
        self.confirm_dialog_message_bind = binding.new_bind()
        self.show_confirm_dialog_bind = binding.new_bind()
        self.error_dialog_message_bind = binding.new_bind()
        self.show_error_dialog_bind = binding.new_bind()
        self.skip_confirmation_bind = binding.new_bind()
        self.run_thread: Any = None

    def set_error(self, message: str) -> None:
        self.view_state.upload_error = message
        self.view_state.upload_failed = True
        self.view_state_bind.update_in_view(self.view_state)

    def clear_error(self) -> None:
        self.view_state.upload_error = ""
        self.view_state.upload_failed = False
        self.view_state_bind.update_in_view(self.view_state)

    def update_view(self) -> None:
        state = self.model.get_job().state
        self.run_btn_disabled = state == job_states.RUNNING or state == job_states.CANCELING
        self.cancel_btn_disabled = state != job_states.RUNNING
        self.config_btn_disabled = self.run_btn_disabled
        self.skip_confirmation = state != job_states.FINISHED_OK

        self.buttons_state_bind.update_in_view(self)
        self.galaxy_running_bind.update_in_view(state == job_states.RUNNING)
        self.skip_confirmation_bind.update_in_view(state != job_states.FINISHED_OK)
        self.config_vm.update_view()
        if state == job_states.FINISHED_OK:
            self.results_vm.update_view()
            self.stitching_vm.update_view()

    async def monitor_run(self) -> None:
        while True:
            current_job = self.model.get_job()
            self.update_view()
            match current_job.state:
                case job_states.FINISHED_OK | job_states.CANCELED:
                    break
                case job_states.FAILED:
                    self.error_dialog_message_bind.update_in_view(
                        "Error during execution. Please review the console error log in the job execution"
                        "tab for more information."
                    )
                    self.show_error_dialog_bind.update_in_view(True)
                    break
            await asyncio.sleep(0.1)

        self.outputs_vm.stop_monitoring()

    def run_in_background(self) -> None:
        self.model.run_in_galaxy()

    def cancel_in_background(self) -> None:
        self.model.cancel_galaxy_job()
        self.run_thread.join()
        self.outputs_vm.stop_monitoring()

    def run(self, confirmed: bool = False) -> None:
        if self.config_vm.view_state.errors:
            self.error_dialog_message_bind.update_in_view(
                "Cannot execute job: invalid configuration. Please review the User Input and Instrument Input Tabs for "
                "validation errors."
            )
            self.show_error_dialog_bind.update_in_view(True)
            return

        if not confirmed:
            folder = self.model.config.output_folder
            messages = []

            if os.environ.get("INSTRUMENT") == "biosans":
                run_cycle = self.model.config.run_cycle
                try:
                    instrument_config = self.model.config.config_type_options[self.model.config.config_type - 2][
                        "title"
                    ]
                except (IndexError, KeyError):
                    instrument_config = None
                sample_env = self.model.config.sample_env

                messages.append(
                    {"text": "Reduction will be run with the following instrument configuration.", "type": "info"}
                )
                messages.append(
                    {
                        "text": f"Run Cycle: {run_cycle}, Instrument: {instrument_config}, Sample Env: {sample_env}",
                        "type": "info",
                    }
                )
                messages.append(
                    {
                        "text": (
                            "If these look incorrect, please use the Instrument Input tab to correct them. If you "
                            "don't know what they should be set to, then please reach out to your local contact."
                        ),
                        "type": "info",
                    }
                )

            if folder_exists_and_not_empty(folder):
                messages.append(
                    {
                        "text": (
                            f"Export folder {self.model.config.output_folder} is not empty. Running will overwrite the "
                            "contents of this directory."
                        ),
                        "type": "warning",
                    }
                )

            if messages:
                self.confirm_dialog_message_bind.update_in_view(messages)
                self.show_confirm_dialog_bind.update_in_view(True)

                return

        self.stitching_vm.set_default_sample()

        self.run_thread = threading.Thread(target=self.run_in_background)
        self.run_thread.daemon = True
        self.run_thread.start()
        asyncio.create_task(self.monitor_run())
        self.outputs_vm.start_monitoring()

    def run_with_overwrite(self) -> None:
        self.show_confirm_dialog_bind.update_in_view(False)
        self.run(confirmed=True)

    def cancel(self) -> None:
        cancel_thread = threading.Thread(target=self.cancel_in_background)
        cancel_thread.daemon = True
        cancel_thread.start()

    def prepare_config_file(self) -> Optional[str]:
        if self.config_vm.view_state.errors:
            self.error_dialog_message_bind.update_in_view(
                "Cannot execute job: invalid configuration. Please review the User Input and Instrument Input Tabs for "
                "validation errors."
            )
            self.show_error_dialog_bind.update_in_view(True)
            return None

        return self.model.prepare_config_file()

    def load_config(self, data: str) -> None:
        self.config_vm.disable_results_pages()
        try:
            self.model.load_config(data)
        except Exception as err:
            self.set_error(str(err))
            return
        self.clear_error()
        self.config_vm.gui_config_updated()
        self.config_vm.update_view()

        self.config_vm.update_oncat()

        self.outputs_vm.reset()
        self.stitching_vm.update_view()

        self.update_view()

    def reset_config(self) -> None:
        self.config_vm.disable_results_pages()
        self.model.reset_config()
        self.config_vm.gui_config_updated()
        self.oncat_vm.reset_samples()
        self.reset_form_bind.update_in_view(None)

        self.outputs_vm.reset()

        self.update_view()
