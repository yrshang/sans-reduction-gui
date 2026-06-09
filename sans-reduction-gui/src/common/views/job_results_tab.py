"""Job results tab."""

from typing import Any

from nova.trame.view.layouts import GridLayout, VBoxLayout
from trame.widgets import vuetify3 as vuetify

from common.view_models.job_results import JobResultsViewModel


class JobResultsTab:
    """Job Reults tab."""

    def __init__(self, server: Any, viewmodel: JobResultsViewModel) -> None:
        self.view_model = viewmodel
        self.view_model.job_results_bind.connect("job_results")
        self.view_model.selected_dataset_bind.connect("selected_dataset")

        self.ctrl = server.controller
        self.state = server.state
        self.state.data = None
        self.state.cur_file_type = None
        self.create_ui()

    def view(self, file: Any) -> None:
        self.view_model.display_file(file)

    def _file_list(self, title: str, var_name: str, preview: bool = True) -> None:
        with vuetify.VList(
            classes="overflow-visible py-0",
            open_strategy="multiple",
            opened=("v" + title.replace(" ", "_"), ["g1"]),
        ):
            with vuetify.VListGroup(value="g1"):
                with vuetify.Template(v_slot_activator="{ props }"):
                    vuetify.VListItem(title=title, v_bind="props")
                with vuetify.VListItem(
                    v_for=f"(file,index) in {var_name}",
                    active=("file.id==selected_dataset.id", False),
                    click=(self.view, "[file]") if preview else None,
                ):
                    vuetify.VListItemTitle("{{ file.name }}", classes="text-wrap")
                    with vuetify.Template(v_slot_append=True):
                        vuetify.VIcon(
                            "mdi-download",
                            click="utils.download(file.name, trigger('download_results', [file.id]))",
                        )

    def create_ui(self) -> None:
        with GridLayout(columns=2, gap="0.5em", stretch=True):
            with VBoxLayout(stretch=True):
                self._file_list("H5 files", "job_results[0]", preview=False)
                self._file_list("1D files", "job_results[1]")
                self._file_list("2D files", "job_results[2]")

            with VBoxLayout(stretch=True):
                vuetify.VTextarea(
                    v_show=("selected_dataset.type === 'text'",), v_model="selected_dataset.content", readonly=True
                )
                vuetify.VImg(
                    v_show=("selected_dataset.type === 'image'",),
                    max_height="100%",
                    max_width="100%",
                    height="auto",
                    src=("selected_dataset.content",),
                    width="auto",
                )

        @self.ctrl.trigger("download_results")
        def get_file(file_id: str) -> Any:
            return self.view_model.get_dataset_content(file_id)
