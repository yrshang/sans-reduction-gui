"""Top level stitching."""

import logging
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Union


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _load_iq_txt(path: Path) -> Any:
    """Load Q, I, dI from a tab/space-delimited 1D reduction output file."""
    import numpy as np
    import types

    data = np.genfromtxt(str(path), comments="#", invalid_raise=False)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    data = data[~np.isnan(data).any(axis=1)]
    if data.shape[0] == 0 or data.shape[1] < 2:
        raise ValueError(f"No valid numeric data in {path}")
    iq = types.SimpleNamespace()
    iq.mod_q = data[:, 0]
    iq.intensity = data[:, 1]
    iq.error = data[:, 2] if data.shape[1] > 2 else np.zeros(data.shape[0])
    return iq


class StitchingModel:
    """Stitching model."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.config: Any = None
        self.merged_iq: Any = None
        self.iqs: List[Any] = []
        self.last_sample_name: str = ""
        self.last_stitching: List[Any] = []
        self.log_axes: List[Any] = []
        self.needs_stitching = True
        self.plots_1D: List[Any] = []
        self.available_profiles: List[Dict[str, Any]] = []
        self.profiles: List[Any] = []
        self.stitching_fname = ""

    def get_log_axes(self) -> List[Any]:
        return self.log_axes

    def get_available_profiles(self) -> List[Dict[str, Any]]:
        return self.available_profiles  # + [{"title": "Other Dataset", "value": "/"}]

    def get_profiles(self) -> List[Any]:
        return self.profiles

    def get_1d_plots(self) -> List[Any]:
        return self.plots_1D

    def update_log_axes(self, index: int, axis: int, value: Any) -> None:
        self.log_axes[index][axis] = value

    def add_profile(self) -> None:
        first_not_selected = 0
        while first_not_selected in self.profiles:
            first_not_selected += 1

        self.profiles.append(first_not_selected)

    def update_profile(self, index: int, value: Any) -> None:
        self.profiles[index] = value

    def delete_profile(self, index: int) -> None:
        if index > 0:
            self.profiles.pop(index + 1)
        else:
            self.profiles.pop(index)

    def load_iq(self, path: str) -> Union[bool, int]:
        from drtsans.mono.gpsans import load_iqmod  # type: ignore[import-not-found]

        try:
            self.iqs.append(load_iqmod(path, header_type="MantidAscii", sep="\t"))
            index = len(self.iqs) - 1

            self.available_profiles.append({"title": path, "value": index})

            return index
        except Exception:
            return False

    def update_1d_plots(self, main_model: Any, sample_name: str, job_results: Any) -> None:
        if not job_results:
            return

        if sample_name != self.last_sample_name:
            self.reset()
            self.last_sample_name = sample_name

        self.config = main_model.config

        if not self.iqs:
            output_1d = Path(main_model.config.output_folder) / "1D"
            if not output_1d.is_dir():
                return
            index = 0
            for fpath in sorted(output_1d.glob("*.txt")):
                try:
                    name = fpath.name
                    if sample_name and sample_name not in name:
                        continue
                    iq = _load_iq_txt(fpath)
                    if "merged" in name.lower() or "combined" in name.lower():
                        self.merged_iq = iq
                    else:
                        self.iqs.append(iq)
                        self.log_axes.append([True, True])
                        self.available_profiles.append({"title": f"Q{index + 1}", "value": index})
                        self.profiles.append(index)
                        index += 1
                except Exception:
                    pass

        for index, _ in enumerate(self.profiles[:-1]):
            if isinstance(self.profiles[index], str):
                res = self.load_iq(self.profiles[index])
                if not res:
                    return
                self.profiles[index] = res
            if isinstance(self.profiles[index + 1], str):
                res = self.load_iq(self.profiles[index + 1])
                if not res:
                    return
                self.profiles[index + 1] = res

        self.plots_1D = []
        for index, _ in enumerate(self.profiles[:-1]):
            self.plots_1D.append(
                {
                    "profile": [f"Q{self.profiles[index] + 1}" for _ in self.iqs[self.profiles[index]].mod_q.tolist()]
                    + [f"Q{self.profiles[index + 1] + 1}" for _ in self.iqs[self.profiles[index + 1]].mod_q.tolist()],
                    "x": self.iqs[self.profiles[index]].mod_q.tolist()
                    + self.iqs[self.profiles[index + 1]].mod_q.tolist(),
                    "y": self.iqs[self.profiles[index]].intensity.tolist()
                    + self.iqs[self.profiles[index + 1]].intensity.tolist(),
                    "error": self.iqs[self.profiles[index]].error.tolist()
                    + self.iqs[self.profiles[index + 1]].error.tolist(),
                }
            )

        if self.merged_iq is not None:
            self.plots_1D.append(
                {
                    "profile": ["Merged" for _ in self.merged_iq.mod_q.tolist()],
                    "x": self.merged_iq.mod_q.tolist(),
                    "y": self.merged_iq.intensity.tolist(),
                    "error": self.merged_iq.error.tolist(),
                }
            )

    def stitch(self) -> Union[str, bool, None]:
        from drtsans.stitch import stitch_profiles  # type: ignore[import-not-found]

        # Have any of the stitching values changed?
        for index, stitching_range in enumerate(self.config.stitching):
            if self.last_stitching and len(self.last_stitching) > index:
                if (
                    stitching_range.min != self.last_stitching[index].min
                    or stitching_range.max != self.last_stitching[index].max
                ):
                    self.needs_stitching = True

        # Have any profiles been added or deleted?
        if self.last_stitching and len(self.profiles) - 1 != len(self.last_stitching):
            self.needs_stitching = True

        if self.needs_stitching:
            self.last_stitching = deepcopy(self.config.stitching)[: len(self.profiles) - 1]
            self.needs_stitching = False

            to_stitch = []
            for index in self.profiles:
                to_stitch.append(self.iqs[index])

            try:
                self.merged_iq = stitch_profiles(
                    profiles=to_stitch,
                    overlaps=[
                        [stitching_range.min, stitching_range.max]
                        for stitching_range in self.config.stitching[: len(to_stitch) - 1]
                    ],
                    target_profile_index=0,
                )

                return True
            except Exception as e:
                logger.error(f"Error stitching profiles: {e}")
                return str(e)
        return None

    def export_stitched_profile(self) -> str:
        from drtsans.mono.gpsans import save_iqmod  # type: ignore[import-not-found]

        with NamedTemporaryFile(mode="w", delete=False) as temp_file:
            save_iqmod(self.merged_iq, temp_file.name, sep="\t")
            return temp_file.name


class SharedStitching:
    """Stitching singleton."""

    _instance = None

    def __new__(cls: Any, *args: Any, **kwargs: Any) -> Any:
        if cls._instance is None:
            cls._instance = StitchingModel()
        return cls._instance
