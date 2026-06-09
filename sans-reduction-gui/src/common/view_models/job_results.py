"""Job results view model."""

import base64
from typing import Any

from nova.mvvm.interface import BindingInterface

from common.models.main import MainModel


class JobResultsViewModel:
    """Job results view model."""

    def __init__(self, model: MainModel, binding: BindingInterface) -> None:
        self.model = model
        self.job_results_bind = binding.new_bind()
        self.selected_dataset_bind = binding.new_bind()
        self.selected_dataset = {"id": None, "type": "", "content": None}

    def update_view(self) -> None:
        job_results = self.model.get_job_results()
        self.job_results_bind.update_in_view(job_results)
        self.selected_dataset_bind.update_in_view(self.selected_dataset)

    def get_dataset_content(self, dataset_id: str) -> Any:
        return self.model.get_dataset_content(dataset_id)

    def display_file(self, file: Any) -> None:
        raw_content = self.get_dataset_content(file["id"])
        if file["type"] == "image":
            image = base64.b64encode(raw_content).decode("utf-8")
            content = f"data:image/jpeg;base64,{image}"
        else:
            content = raw_content.decode("utf-8")
        self.selected_dataset = {"id": file["id"], "type": file["type"], "content": content}
        self.update_view()
