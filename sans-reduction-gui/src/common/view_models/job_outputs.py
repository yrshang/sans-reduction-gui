"""Job outputs related view model and functions."""

import asyncio
from typing import Any, Dict

from nova.mvvm.interface import BindingInterface

from common.models.job import job_states
from common.models.main import MainModel


def dict_from_job(job: Any) -> Dict[str, Any]:
    job_progress = "0"
    details = job.state_details
    if "uploading" in details:
        job_progress = "10"
    if "starting" in details:
        job_progress = "20"
    if "waiting" in details:
        job_progress = "50"
    if "exporting" in details:
        job_progress = "80"

    show_progress = job.state in [job_states.RUNNING, job_states.CANCELING]
    show_failed = job.state == job_states.FAILED
    show_ok = job.state == job_states.FINISHED_OK

    return {
        "output": job.output,
        "error": job.error,
        "show_failed": show_failed,
        "show_progress": show_progress,
        "show_ok": show_ok,
        "progress": job_progress,
        "state_details": job.state_details,
        "state": job.state,
    }


class JobOutputsViewModel:
    """Job outputs view model."""

    def __init__(self, model: MainModel, binding: BindingInterface) -> None:
        self.model = model
        self.monitoring_task: Any = None
        self.scroll_position = {"job-outputs": 0, "job-errors": 0}
        self.job_output_bind = binding.new_bind()
        self.scroll_position_bind = binding.new_bind(self.scroll_position, ["job-outputs", "job-errors"])
        self.scroll_bind = binding.new_bind()

    async def monitor_output(self) -> None:
        while True:
            await asyncio.sleep(1)
            self.model.update_job_output()
            self.update_view()

    def update_view(self) -> None:
        job = dict_from_job(self.model.get_job())
        self.job_output_bind.update_in_view(job)
        self.scroll_position_bind.update_in_view(self.scroll_position)
        if job["state"] == job_states.RUNNING:
            self.scroll_bind.update_in_view("job-outputs")
            self.scroll_bind.update_in_view("job-errors")

    def reset(self) -> None:
        self.model.reset_job()
        self.update_view()

    def start_monitoring(self) -> None:
        self.monitoring_task = asyncio.create_task(self.monitor_output())

    def stop_monitoring(self) -> None:
        self.monitoring_task.cancel()
        self.update_view()
