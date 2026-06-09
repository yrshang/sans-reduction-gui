"""ONCat view model."""

from typing import Any, Callable, Dict, List, Optional

from nova.mvvm.interface import BindingInterface
from pydantic import BaseModel, Field


class ViewState(BaseModel):
    """Pydantic model for ONCat view state."""

    available_experiments: List[Any] = Field(default=[])
    available_samples: Dict[str, Any] = Field(default={})
    available_sample_headers: List[Dict[str, Any]] = Field(default=[])
    available_sample_items: List[Dict[str, Any]] = Field(default=[])
    error: bool = Field(default=False)
    previews: Dict[str, Any] = Field(default={})
    search_items: List[Dict[str, Any]] = Field(default=[])
    updating: bool = Field(default=False)


class ONCatViewModel:
    """ONCat view model."""

    ONCAT_UPDATE_INTERVAL = 60

    def __init__(self, model: Any, binding: BindingInterface) -> None:
        self.model = model
        self.binding = binding

        self.search_results: List[Any] = []

        self.view_state = ViewState()
        self.view_state_bind = binding.new_bind(self.view_state)

    def clear_error(self) -> None:
        self.view_state.error = False
        self.view_state_bind.update_in_view(self.view_state)

    def get_previews(self, runs: list[dict[str, Any]]) -> None:
        for run in runs:
            key = run["run_number"]
            if key not in self.view_state.previews or "error" in self.view_state.previews[key]:
                preview = self.model.get_preview(run)
                self.view_state.previews[key] = preview

        self.update_view()

    def get_run_number(self, run_text: str) -> None:
        try:
            run_number = int(run_text)
        except Exception:
            return

        run_data = self.model.get_run_number(run_number)

        if run_data:
            self.search_results = [run_data]
            self.update_search_items()
            self.update_view()

    def update_experiments(self) -> None:
        self.view_state.available_experiments = self.model.get_experiments()
        self.update_view()

    def update_samples(self, ipts_number: str, progress: Callable) -> Dict[int, str]:
        self.view_state.available_samples = self.model.get_samples(ipts_number)
        self.view_state.available_sample_headers = [
            {"key": "name", "title": "Sample"},
            {"key": "thickness", "title": "Thickness (mm)"},
            {"key": "attenuator", "title": "Attenuator"},
            {"key": "guides", "title": "# Guides"},
            {"key": "runs", "title": "Runs"},
            {"key": "transmission", "title": "Transmission"},
        ]
        self.view_state.available_sample_items = sorted(
            self.view_state.available_samples.values(),
            key=lambda sample: sample.get("name", "").lower(),
        )
        self.update_search_items()
        self.view_state.updating = False

        samples_by_run_number: Dict[int, Any] = {}
        for name, sample in self.view_state.available_samples.items():
            for run in sample["runs"]:
                index = run["run_number"]
                samples_by_run_number[index] = name
            for trans in sample["transmission"]:
                index = trans["run_number"]
                samples_by_run_number[index] = name

        return samples_by_run_number

    def update_search_items(self) -> None:
        self.view_state.search_items = self.view_state.available_sample_items + self.search_results

    def reset_samples(self) -> None:
        self.view_state.available_samples = {}
        self.view_state.available_sample_headers = []
        self.view_state.available_sample_items = []
        self.search_results = []
        self.update_search_items()

        self.update_view()

    def set_updating(self, updating: bool) -> None:
        self.view_state.updating = updating
        self.update_view()

    def update_selected_samples(self, sample_names: list[str], index: Optional[int] = None) -> None:
        self.model.config.set_samples([self.view_state.available_samples[name] for name in sample_names], index)

    def update_view(self) -> None:
        self.view_state.error = self.model.get_oncat_error_state()
        self.view_state_bind.update_in_view(self.view_state)
