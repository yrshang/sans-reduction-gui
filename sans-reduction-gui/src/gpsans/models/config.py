"""Common configuration classes and functions."""

import csv
import getpass
import json
import os
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, ValidationInfo, computed_field, field_validator

from common.models.config import QRangeCleanCurves, StitchingRange


def sniff(value: Any) -> Union[str, Type[csv.Dialect]]:
    try:
        return csv.Sniffer().sniff(value, delimiters=", \t")
    except csv.Error:
        return "excel"


def parse_list(data: str) -> list[str]:
    return list(next(csv.reader([data], dialect=sniff(data), skipinitialspace=True)))


class QRange(BaseModel):
    """QRange represents the config for a single detector configuration."""

    samples: List[str] = Field(default=[])
    thicknesses: List[float] = Field(default=[])
    background_sample: Optional[Dict[str, Any]] = Field(default=None, title="Background Sample")
    beam_center_sample: Optional[Dict[str, Any]] = Field(default=None, title="Beam Center Sample")
    empty_beam_sample: Optional[Dict[str, Any]] = Field(default=None, title="Empty Beam Sample")
    block_beam_sample: Optional[Dict[str, Any]] = Field(default=None, title="Blocked Beam Sample")
    samples_config: list[str] = Field(
        default=[],
        title="Sample Config",
        description=(
            "The run number for the sample scattering to be reduced. It is possible to specify a set of scattering "
            "runs for a single sample that are to be summed together into a single data set for reduction. To do so, "
            "use the following format, which uses a single pair of quotes to enclose the list: "
            "&quot;runNumber&quot;:&quot;XXXXXX, YYYYYY&quot;"
        ),
        examples=["123456, 234567"],
    )
    samples_trans_config: list[str] = Field(
        default=[],
        title="Sample Trans Config",
        description=(
            "This is the run number of the transmission for the sample. There can only be a single run number "
            "specified here."
        ),
        examples=["123456, 234567"],
    )
    bkgd_config: list[str] = Field(
        default=[],
        title="Background Config",
        description="The run number of the background data to subtract from the sample scattering.",
        examples=["123456, 234567"],
    )
    bkgd_trans_config: list[str] = Field(
        default=[],
        title="Background Trans Config",
        description=(
            "The run number for the background's transmission measurement. If no background is specified, then this "
            "run number should not be specified (i.e. set to &quot;&quot;)."
        ),
        examples=["123456, 234567"],
    )
    beam_center_config: Optional[Union[int, str]] = Field(
        default=None,
        title="Beam Center Config",
        description="This is the run number of an empty beam or a transmission measurement. It cannot be left blank.",
        examples=["123456"],
    )
    empty_trans_config: Optional[Union[int, str]] = Field(
        default=None,
        title="Empty Trans Config",
        description="The run number for the background's transmission measurement.",
        examples=["123456"],
    )
    use_mask_file: bool = Field(default=True, title="Use Mask File")
    mask_file_name: str = Field(
        default="",
        title="Mask File Name",
        description=(
            "This is the name of a hand-drawn mask. Your local contact can help you prepare a mask for your specific "
            "experiment."
        ),
        examples=["/SNS/path/to/mask.xml"],
    )
    use_dark_file: bool = Field(default=True, title="Use Dark File")
    dark_file_name: str = Field(
        default="",
        title="Dark File Name",
        description=(
            "This parameter specifies the name of the file that contains the &quot;dark current&quot; measurement, "
            "which is normally a measurement performed either during regular calibrations with the facility running "
            "but the instrument shutter closed or during your experiment in case non-standard instrument "
            "configurations is used. It is a measure of cosmic radiation and detector electronic noise. Your local "
            "contact will help you find the correct file to use."
        ),
        examples=["/SNS/path/to/dark_current.xml"],
    )
    block_beam: Optional[str] = Field(
        default="",
        title="Blocked Beam",
        description="Run number for blocked beam. Contact your local contact if you need to use this run number.",
        examples=["123456"],
    )
    use_mask_back_tubes: bool = Field(default=False, title="Use Mask Back Tubes")
    wavelength: Optional[str] = Field(
        default=None,
        title="Wavelength",
        description=(
            "Use this if the wavelength saved to the metadata needs to be overwritten. This should only be done with "
            "your local contact."
        ),
        examples=["/SNS/path/to/wavelength.xml"],
    )
    wavelength_spread: Optional[str] = Field(
        default=None,
        title="Wavelength Spread",
        description=(
            "The spread of the wavelength. This value should be constant. Contact your local contact if you want to "
            "change it."
        ),
        examples=["0.1"],
    )

    @field_validator("samples_config", "samples_trans_config", "bkgd_config", "bkgd_trans_config", mode="before")
    @classmethod
    def validate_sample_runs(cls, run_numbers: Union[str, list[str]]) -> list[str]:
        if isinstance(run_numbers, str):
            run_numbers = parse_list(str(run_numbers))

        for run in run_numbers:
            if "," in run:
                for value in run.split(","):
                    int(value)
            else:
                int(run)

        return run_numbers

    @field_validator("mask_file_name", mode="after")
    @classmethod
    def validate_mask_file(cls, mask_file_name: str, info: ValidationInfo) -> str:
        if info.data["use_mask_file"] and not mask_file_name:
            raise ValueError("Mask file name must be specified.")
        return mask_file_name

    @field_validator("dark_file_name", mode="after")
    @classmethod
    def validate_dark_file(cls, dark_file_name: str, info: ValidationInfo) -> str:
        if info.data["use_dark_file"] and not dark_file_name:
            raise ValueError("Dark file name must be specified.")
        return dark_file_name

    def reset(self) -> None:
        for field, field_info in self.model_fields.items():
            setattr(self, field, field_info.default)
        self.model_fields_set.clear()

    def set_samples(self, samples: List[Dict[str, Any]]) -> None:
        self.samples = [sample["name"] for sample in samples]
        self.thicknesses = [sample["thickness"] / 10.0 for sample in samples]

        runs = []
        transmissions = []
        for sample in samples:
            runs.extend(sample.get("runs", []))
            transmissions.extend(sample.get("transmission", []))

        if runs:
            self.samples_config = [str(run["run_number"]) for run in runs]
        else:
            self.samples_config = []

        if transmissions:
            self.samples_trans_config = [str(trans["run_number"]) for trans in transmissions]
        else:
            self.samples_trans_config = self.samples_config

    def update_background(self) -> None:
        if self.background_sample and "runs" in self.background_sample:
            self.bkgd_config = [str(run["run_number"]) for run in self.background_sample["runs"]]
            self.bkgd_trans_config = [str(run["run_number"]) for run in self.background_sample["transmission"]]
            if not self.bkgd_trans_config:
                self.bkgd_trans_config = self.bkgd_config
            if not self.bkgd_config:
                self.bkgd_config = self.bkgd_trans_config

    def update_beam_center(self) -> None:
        if self.beam_center_sample and "runs" in self.beam_center_sample:
            if self.beam_center_sample["runs"]:
                self.beam_center_config = self.beam_center_sample["runs"][0]["run_number"]
            elif self.beam_center_sample["transmission"]:
                self.beam_center_config = self.beam_center_sample["transmission"][0]["run_number"]
            else:
                self.beam_center_config = None

    def update_empty_beam(self) -> None:
        if self.empty_beam_sample and "runs" in self.empty_beam_sample:
            if self.empty_beam_sample["runs"]:
                self.empty_trans_config = self.empty_beam_sample["runs"][0]["run_number"]
            elif self.empty_beam_sample["transmission"]:
                self.empty_trans_config = self.empty_beam_sample["transmission"][0]["run_number"]
            else:
                self.empty_trans_config = None

    def update_block_beam(self) -> None:
        if self.block_beam_sample and "runs" in self.block_beam_sample:
            if self.block_beam_sample["runs"]:
                self.block_beam = str(self.block_beam_sample["runs"][0]["run_number"])
            elif self.block_beam_sample["transmission"]:
                self.block_beam = str(self.block_beam_sample["transmission"][0]["run_number"])
            else:
                self.block_beam = None


class GPSANSConfig(BaseModel):
    """Pydantic model for GPSANS."""

    # The GPSANS detector can be manually moved by the IS to collect data over multiple q-ranges.
    MAX_RANGES_NUM: int = 4
    MIXED_TYPE_INTS: list[str] = ["beam_center_config", "empty_trans_config"]
    MIXED_TYPE_LISTS: list[str] = [
        "samples_config",
        "samples_trans_config",
        "bkgd_config",
        "bkgd_trans_config",
    ]
    ranges: list[QRange] = Field(default=[])

    # Galaxy config
    tool_id: str = "neutrons_gpsans"

    # ONCat config
    facility: str = "HFIR"
    instrument: str = "CG2"
    ipts_number: str = Field(default="", title="IPTS Number", examples=["33700"])

    # drtsans config
    output_folder: str = Field(
        default="/HFIR",
        title="Output Folder",
        description=(
            "The directory to write the data reduction result to is listed here. Normally, it would be the shared "
            "directory for the particular proposal, which allows other team members and the local contact to view the "
            "results. However, it is also possible to specify a location in a user's home directory. It is left to the "
            "discretion of the user."
        ),
        examples=["/SNS/path/to/output/folder"],
    )
    sample_names: list[str] = Field(
        default=[],
        title="Sample Names",
        description=(
            "This is the base used to construct all of the file names that result from the data reduction process. For "
            "example, all of the files will be named &quot;sample_name*.*&quot;. The filename can be any valid string "
            "that is acceptable for filenames for a Linux operating system."
        ),
        examples=["Annealed_PTEO"],
    )
    stitching_sample: str = Field(default="")
    sample_thick: list[float] = Field(
        default=[],
        title="Sample Thickness",
        description=(
            "This parameter specifies the sample thickness in centimeters. Note that the value is not enclosed in "
            "quotes."
        ),
        examples=["0.1, 0.2"],
    )
    see_full_verbose: bool = Field(default=False, title="See Full Verbose")
    use_log_2d_binning: bool = Field(default=True, title="Use Log 2D Binning")
    background_sample: Optional[dict[str, Any]] = Field(default=None, title="Background Sample")
    beam_center_sample: Optional[dict[str, Any]] = Field(default=None, title="Beam Center Sample")
    empty_beam_sample: Optional[dict[str, Any]] = Field(default=None, title="Empty Beam Sample")

    # Q-ranges and overlaps
    q_range_clean_curves: list[QRangeCleanCurves] = Field(default=[])
    stitching: list[StitchingRange] = Field(default=[])

    # Misc. configuration
    common_configuration: dict[str, Any] = {
        "emptyTransmission": {"runNumber": ""},
        "beamCenter": {"runNumber": ""},
        "configuration": {
            "sampleOffset": None,
            "useDetectorOffset": False,
            "detectorOffset": 0.0,
            "sampleDetectorDistance": None,
            "sampleToSi": None,
            "sampleApertureSize": None,
            "sourceApertureDiameter": None,
            "usePixelCalibration": True,
            "useDefaultMask": True,
            "defaultMask": [{"Pixel": "1-10,247-256"}],
            "normalization": "Monitor",
            "sensitivityFileName": "/HFIR/CG2/shared/drt_sensitivity/sens_c499_bar.nxs",
            "blockedBeamRunNumber": "",
            "DBScalingBeamRadius": 40,
            "mmRadiusForTransmission": 40,
            "absoluteScaleMethod": "standard",
            "StandardAbsoluteScale": 3.49e-11,
            "numQxQyBins": 90,
            "1DQbinType": "scalar",
            "QbinType": "log",
            "numQBins": None,
            "LogQBinsPerDecade": 33,
            "useLogQBinsDecadeCenter": True,
            "useLogQBinsEvenDecade": False,
            "useSubpixels": True,
            "subpixelsX": 1,
            "subpixelsY": 1,
        },
    }

    @computed_field  # type: ignore
    @property
    def base_path(self) -> str:
        return f"/{self.facility}/{self.instrument}"

    @computed_field  # type: ignore
    @property
    def can_add_range(self) -> bool:
        return len(self.ranges) < self.MAX_RANGES_NUM

    @computed_field  # type: ignore
    @property
    def can_remove_range(self) -> bool:
        return len(self.ranges) > 1

    @field_validator("output_folder", mode="after")
    @classmethod
    def validate_output_folder(cls, output_folder: str) -> str:
        if not output_folder.startswith("/HFIR") and not output_folder.startswith("/SNS"):
            raise ValueError("The output folder must start with /HFIR or /SNS.")

        return output_folder

    @field_validator("sample_names", "sample_thick", mode="before")
    @classmethod
    def parse_sample_data(cls, sample_data: Union[str, list[Any]]) -> list[Any]:
        if isinstance(sample_data, str):
            parsed_names = parse_list(sample_data)
        else:
            parsed_names = sample_data

        return parsed_names

    def reset(self) -> None:
        default_model = GPSANSConfig()
        for field, value in default_model:
            if field not in ["ranges", "stitching", "q_range_clean_curves"]:
                setattr(self, field, value)

        while len(self.ranges) > 1:
            self.ranges.pop()
            self.q_range_clean_curves.pop()
            self.stitching.pop()

        self.ranges[0].reset()
        self.q_range_clean_curves[0].reset()
        self.stitching[0].reset()

        self.model_fields_set.clear()

    def parse_run_number(self, value: Any) -> Union[int, str]:
        if isinstance(value, int):
            return value
        elif isinstance(value, str):
            if "," in value:
                return value
            else:
                return int(value)
        else:
            raise TypeError(f"Unexpected type {type(value)} in config file")

    def parse_q_values(self, values: Any, num: Any) -> QRange:
        q_range = QRange()
        for key in q_range.model_fields:
            if f"{key}_{num}" in values:
                value = values[f"{key}_{num}"]

                if key in self.MIXED_TYPE_LISTS:
                    parsed_values = []
                    for item in value:
                        parsed_values.append(self.parse_run_number(item))
                    value = str(parsed_values).strip("[]")
                elif key in self.MIXED_TYPE_INTS:
                    value = str(value)

                setattr(q_range, key, value)

        return q_range

    def load_old_config(self, config_data: str) -> dict[str, Any]:
        config_dict: dict[str, Any] = {}
        exec(config_data, {}, config_dict)
        self.ranges = []
        self.q_range_clean_curves = []
        self.stitching = []
        self.ipts_number = str(config_dict.get("ipts_number", ""))

        self.output_folder = config_dict.get("output_folder", "")

        self.sample_names = config_dict.get("sample_names", [])
        self.sample_thick = config_dict.get("sample_thick", [])

        self.see_full_verbose = config_dict.get("see_full_verbose", False)
        self.use_log_2d_binning = config_dict.get("use_log_2d_binning", True)

        if "common_configuration" in config_dict:
            self.common_configuration = config_dict["common_configuration"]

        q_range_num = config_dict.get("config_num", self.MAX_RANGES_NUM)

        for i in range(0, q_range_num):
            q_range = self.parse_q_values(config_dict, i + 1)
            if q_range:
                self.ranges.append(q_range)
            else:
                break

        for i in range(0, q_range_num - 1):
            st = f"stitching_q_{i + 1}_{i + 2}"
            if st in config_dict:
                self.stitching.append(StitchingRange(min=config_dict[st][0], max=config_dict[st][1]))
            else:
                break

        for i in range(0, q_range_num):
            st = f"q_range_{i + 1}"
            if st in config_dict:
                self.q_range_clean_curves.append(QRangeCleanCurves(min=config_dict[st][0], max=config_dict[st][1]))
            else:
                break

        return config_dict

    def load_config(self, config_data: str) -> dict[str, Any]:
        try:
            config_dict = json.loads(config_data)

            self.ranges = []
            self.stitching = []
            self.q_range_clean_curves = []
            for index, range in enumerate(config_dict["ranges"]):
                self.add_range()

                for key in range:
                    setattr(self.ranges[index], key, range[key])

            for index, stitching_range in enumerate(config_dict["stitching"]):
                for key in stitching_range:
                    setattr(self.stitching[index], key, stitching_range[key])

            for index, q_range_clean_curves in enumerate(config_dict["q_range_clean_curves"]):
                for key in q_range_clean_curves:
                    setattr(self.q_range_clean_curves[index], key, q_range_clean_curves[key])

            for key in config_dict:
                if key not in ["ranges", "stitching", "q_range_clean_curves", "common_configuration"]:
                    setattr(self, key, config_dict[key])
            if "common_configuration" in config_dict:
                self.common_configuration = config_dict["common_configuration"]
        except ValueError:
            config_dict = self.load_old_config(config_data)

        return config_dict

    def update_sample_selections(self, available_samples: Dict[int, str]) -> None:
        # For older config files, we need to map the run numbers to samples from ONCat.
        # TODO: clean this up on Monday, lots of repetition here
        for range in self.ranges:
            if not range.samples:
                for run in range.samples_config:
                    value = available_samples.get(int(run), None)
                    if value is not None and value not in range.samples:
                        range.samples.append(value)
                for trans in range.samples_trans_config:
                    value = available_samples.get(int(trans), None)
                    if value is not None and value not in range.samples:
                        range.samples.append(value)

            if not range.background_sample:
                for run in range.bkgd_config:
                    value = available_samples.get(int(run), None)
                    if value is not None:
                        range.background_sample = {"name": value}
                for trans in range.bkgd_trans_config:
                    value = available_samples.get(int(trans), None)
                    if value is not None:
                        range.background_sample = {"name": value}

            if not range.beam_center_sample:
                if range.beam_center_config:
                    range.beam_center_sample = {"name": available_samples.get(range.beam_center_config, "")}

            if not range.empty_beam_sample:
                if range.empty_trans_config:
                    range.empty_beam_sample = {"name": available_samples.get(range.empty_trans_config, "")}

            if not range.block_beam_sample:
                if range.block_beam:
                    range.block_beam_sample = {"name": available_samples.get(int(range.block_beam), "")}

    def prepare_config_file(self) -> str:
        return self.model_dump_json(
            exclude={
                "MAX_RANGES_NUM",
                "MIXED_TYPE_INTS",
                "MIXED_TYPE_LISTS",
                "tool_id",
                "facility",
                "instrument",
                "base_path",
                "can_add_range",
                "can_remove_range",
            },
            indent=2,
        )

    def prepare_drtsans_config(self) -> List[dict]:
        configs = []
        for q_range in self.ranges:
            for n, run_number in enumerate(q_range.samples_config):
                config = {
                    "instrumentName": "GPSANS",
                    "iptsNumber": self.ipts_number,
                    "sample": {
                        "runNumber": run_number,
                        "thickness": q_range.thicknesses[n] if n < len(q_range.thicknesses) else 1.0,
                        "transmission": {"runNumber": q_range.samples_trans_config[n]}
                        if q_range.samples_trans_config
                        else {},
                    },
                    "background": {
                        "runNumber": q_range.bkgd_config[0] if q_range.bkgd_config else "",
                        "transmission": {"runNumber": q_range.bkgd_trans_config[0]}
                        if q_range.bkgd_trans_config
                        else {},
                    },
                    "beamCenter": {"runNumber": q_range.beam_center_config},
                    "emptyTransmission": {"runNumber": q_range.empty_trans_config},
                    "outputFileName": self.ranges[0].samples[n]
                    if n < len(self.ranges[0].samples)
                    else f"sample_{n}",
                    "configuration": {
                        "outputDir": self.output_folder,
                        "maskFileName": q_range.mask_file_name,
                        "darkFileName": q_range.dark_file_name,
                        "useMaskBackTubes": q_range.use_mask_back_tubes,
                        **self.common_configuration.get("configuration", {}),
                    },
                }
                configs.append(config)
        return configs

    def add_range(self) -> None:
        q_range = QRange()

        new_index = len(self.ranges)
        match new_index:
            case 0:
                q_range.mask_file_name = "/HFIR/CG2/shared/Lilin/Masks/CG2_69806.nxs"
                q_range.dark_file_name = "/HFIR/CG2/shared/Lilin/Masks/CG2_68950.nxs.h5"
                self.q_range_clean_curves.append(QRangeCleanCurves(max=0.1, min=0.0015))
            case 1:
                q_range.mask_file_name = "/HFIR/CG2/shared/Lilin/Masks/CG2_69718.nxs"
                q_range.dark_file_name = "/HFIR/CG2/shared/Lilin/Masks/CG2_68951.nxs.h5"
                self.q_range_clean_curves.append(QRangeCleanCurves(max=0.13, min=0.008))
            case 2:
                q_range.mask_file_name = "/HFIR/CG2/shared/Lilin/Masks/CG2_69736.nxs"
                q_range.dark_file_name = "/HFIR/CG2/shared/Lilin/Masks/CG2_68952.nxs.h5"
                q_range.use_mask_back_tubes = True
                self.q_range_clean_curves.append(QRangeCleanCurves(max=1.4, min=0.075))
            case 3:
                q_range.mask_file_name = ""
                q_range.dark_file_name = "/HFIR/CG2/shared/Lilin/DC/CG2_8844.nxs.h5"
                q_range.use_mask_back_tubes = True
                self.q_range_clean_curves.append(QRangeCleanCurves(max=1.0, min=0.07))

        self.stitching.append(StitchingRange())
        self.ranges.append(q_range)

    def reduce_n_ranges(self) -> None:
        self.ranges.pop()
        self.q_range_clean_curves.pop()
        self.stitching.pop()

    def update_output_folder(self) -> None:
        self.output_folder = (
            f"{self.base_path}/IPTS-{self.ipts_number}/shared/"
            f"{getpass.getuser()}/ReductionOutput/"
        )

    def set_samples(self, samples: List[Dict[str, Any]], index: Optional[int]) -> None:
        if index is not None:
            self.ranges[index].set_samples(samples)

        self.sample_thick = self.ranges[0].thicknesses
        self.sample_names = self.ranges[0].samples

    def update_background(self, index: Optional[int]) -> None:
        if index is not None:
            self.ranges[index].update_background()

    def update_beam_center(self, index: Optional[int]) -> None:
        if index is not None:
            self.ranges[index].update_beam_center()

    def update_empty_beam(self, index: Optional[int]) -> None:
        if index is not None:
            self.ranges[index].update_empty_beam()

    def update_block_beam(self, index: Optional[int]) -> None:
        if index is not None:
            self.ranges[index].update_block_beam()


class SharedConfig:
    """Config Singleton."""

    _instance = None

    def __new__(cls: Any, *args: Any, **kwargs: Any) -> Any:
        if cls._instance is None:
            cls._instance = GPSANSConfig()
            cls._instance.add_range()
        return cls._instance
