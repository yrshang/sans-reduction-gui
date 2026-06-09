"""Main model."""

import logging
from typing import Any, Dict, List, Optional, Union

from common.models import DictObject
from common.models.local_reduction import SharedLocalReduction
from common.models.job import SharedJob, job_states
from common.models.oncat import SharedONCat
from common.models.stitching import SharedStitching

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MainModel(DictObject):
    """Main model class."""

    def __init__(self, config_class: Any, args: Any) -> None:
        self.config_class = config_class
        self.config = config_class(args)
        self._galaxy: Any = SharedLocalReduction()
        self._job: Any = SharedJob()
        self._oncat: Any = SharedONCat(facility=self.config.facility, instrument=self.config.instrument)
        self._stitching: Any = SharedStitching()
        self._datasets_cache: Dict[Any, Any] = {}

    def load_config(self, config_data: Any) -> None:
        self.config.load_config(config_data)

    def reset_config(self) -> None:
        self.config.reset()

    def update_sample_selections(self, samples_by_run_number: Dict[int, str]) -> None:
        self.config.update_sample_selections(samples_by_run_number)

    def reset_job(self) -> None:
        self._job.reset()

    def update_keeping_types(self, config_data: Any) -> None:
        self.config.update_keeping_types(config_data)

    def prepare_config_file(self) -> str:
        return self.config.prepare_config_file()

    def get_job(self) -> SharedJob:
        return self._job

    def get_job_results(self) -> Any:
        return self._galaxy.get_job_results(self.config)

    def get_preview(self, run: dict[str, Any]) -> dict[str, Any]:
        return self._oncat.get_preview(run)

    def get_run_number(self, run_number: str) -> None:
        return self._oncat.get_run_number(run_number)

    def get_max_ranges(self) -> int:
        return self.config.MAX_RANGES_NUM

    def get_log_axes(self) -> List[Any]:
        return self._stitching.get_log_axes()

    def get_available_stitching_profiles(self) -> List[Any]:
        return self._stitching.get_available_profiles()

    def get_stitching_profiles(self) -> List[Any]:
        return self._stitching.get_profiles()

    def get_1d_plots(self) -> List[Any]:
        return self._stitching.get_1d_plots()

    def update_log_axes(self, index: int, axis: int, value: Any) -> None:
        self._stitching.update_log_axes(index, axis, value)

    def add_stitching_profile(self) -> None:
        self._stitching.add_profile()

    def update_stitching_profile(self, index: int, value: Any) -> None:
        self._stitching.update_profile(index, value)

    def delete_stitching_profile(self, index: int) -> None:
        self._stitching.delete_profile(index)

    def update_1d_plots(self, sample_name: str, job_results: Any) -> None:
        self._stitching.update_1d_plots(self, sample_name, job_results)

    def get_dataset_content(self, dataset_id: str) -> Any:
        dataset_content = self._datasets_cache.get(dataset_id, None)
        if dataset_content:
            return dataset_content

        try:
            content = self._galaxy.get_dataset_content(dataset_id)
            self._datasets_cache[dataset_id] = content
            return content
        except Exception as e:
            print(e)

    def cancel_galaxy_job(self) -> None:
        self._job.state = job_states.CANCELING
        self._job.state_details = "canceling job"
        try:
            self._galaxy.cancel_job(self._job)
        except Exception as e:
            print(f"Error canceling job:{e}")

    def run_in_galaxy(self) -> None:
        self._job.reset()
        self._stitching.reset()
        self._datasets_cache = {}
        self._job.state = job_states.RUNNING
        try:
            self._galaxy.run_reduction(self.config, self._job)
            self._job.state = job_states.FINISHED_OK if self._job.state != job_states.CANCELING else job_states.CANCELED
        except Exception as e:
            if self._job.state == job_states.CANCELING:
                self._job.state = job_states.CANCELED
                self._job.error = ""
            else:
                self._job.state = job_states.FAILED
                self._job.state_details = "Job failed"
                self._job.error += str(e)

    def get_galaxy_url(self) -> str:
        return self._galaxy.galaxy_url

    def update_job_output(self) -> None:
        if self._job.tool and not self._job.reduction_complete:
            try:
                self._galaxy.get_job_outputs(self._job)
            except Exception as e:
                print(e)

    def get_oncat_error_state(self) -> bool:
        return self._oncat.get_error_state()

    def get_experiments(self) -> Any:
        return self._oncat.get_experiments()

    def get_samples(self, ipts_number: str) -> Any:
        return self._oncat.get_samples(ipts_number)

    def update_overlap(self, index: int, interval: list[float]) -> None:
        self.config.stitching[index].min = interval[0]
        self.config.stitching[index].max = interval[1]

    def stitch(self) -> Union[bool, str]:
        return self._stitching.stitch()

    def export_stitched_profile(self) -> Optional[Dict[str, Any]]:
        iqmod_fname = self._stitching.export_stitched_profile()
        if iqmod_fname is not None:
            export_fname = f"{self.config.sample_names[0] if self.config.sample_names else 'stitching'}_merged.txt"
            return self._galaxy.upload_file(iqmod_fname, self.config, self._job, export_fname)
        return None
