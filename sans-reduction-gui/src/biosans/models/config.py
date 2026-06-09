"""BioSANS Config."""

import getpass
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator
from typing_extensions import Self

from common.models.config import StitchingRange

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BioSANSConfig(BaseModel):
    """Pydantic model for BioSANS."""

    # BioSANS instrument has 3 fixed q-ranges for main, midrange, and wing detectors
    ranges: list[Any] = [None, None, None]
    MAX_RANGES_NUM: int = 3

    # Galaxy config
    tool_id: str = "neutrons_biosans"

    # ONCat config
    facility: str = "HFIR"
    instrument: str = "CG3"
    ipts_number: str = Field(default="", title="Select Your Experiment")

    # User Inputs
    background_sample: Optional[dict[str, Any]] = Field(default=None, title="Background Sample")
    beam_center_sample: Optional[dict[str, Any]] = Field(default=None, title="Beam Center Sample")
    empty_beam_sample: Optional[dict[str, Any]] = Field(default=None, title="Empty Beam Sample")
    output_folder: str = Field(default="/HFIR", title="Output Folder")
    sample_names: list[str] = []

    # Instrument Inputs
    valid_configurations: dict[int, dict[int, dict[str, str]]] = {}
    run_cycle: int = Field(default=510, title="Run Cycle")
    run_cycle_options: list[int] = []
    config_type: int = Field(default=2, title="Instrument Configuration")
    config_type_options: list[dict[str, Any]] = []
    sample_env: str = Field(default="URBj", title="Sample Environment")
    sample_env_options: list[str] = []
    config_path: str = ""
    flexible_pixelsizes: bool = Field(default=False, title="Use Flexible Pixelsizes")
    wavelength: Optional[float] = Field(
        default=None,
        title="Wavelength",
        description=(
            "Wavelength in Angstrom, it is can be specified or leave as null, in which the meta data value in the raw "
            "data file will be used."
        ),
        examples=[6.0],
    )

    # drtsans config
    samples: list[str] = []
    samples_thickness: list[float] = []
    samples_transmission: list[str] = []
    backgrounds: list[str] = []
    backgrounds_transmission: list[str] = []
    beam_center: Optional[str] = None
    empty_beam: Optional[str] = None

    # Q-ranges and overlaps
    q_range_main: list[float] = [0.0, 0.0]
    q_range_midr: list[float] = [0.0, 0.0]
    q_range_wing: list[float] = [0.0, 0.0]
    OL_range_Qmax: list[float] = [0.0, 0.0]
    OL_range_Qmin: list[float] = [0.0, 0.0]
    stitching: list[StitchingRange] = []
    stitching_sample: str = Field(default="", title="Sample to Stitch")

    # Misc. configuration
    common_configuration: dict[str, Any] = {
        "configuration": {
            "StandardAbsoluteScale": [2.7e-10],
            "darkMainFileName": "CG3_26798.nxs.h5",
            "darkMidrangeFileName": "CG3_CG3_26798.nxs.h5",
            "darkWingFileName": "CG3_26798.nxs.h5",
            "sampleToSi": None,
            "sensitivityMainFileName": "",
            "sensitivityMidrangeFileName": "",
            "sensitivityWingFileName": "",
            "defaultMask": [
                {"Pixel": "1-18,239-256"},
                {"Bank": "98", "Tube": "4"},
            ],
            "maskFileName": None,
            "DBScalingBeamRadius": None,
            "mmRadiusForTransmission": "",
            "normalization": "Monitor",
            "absoluteScaleMethod": "standard",
            "wavelength": None,
            "wavelengthSpread": None,
            "numMainQBins": "",
            "numMidrangeQBins": "",
            "numWingQBins": "",
            "numMainQxQyBins": 100,
            "numMidrangeQxQyBins": 100,
            "numWingQxQyBins": 100,
            "1DQbinType": "scalar",
            "QbinType": "log",
            "LogQBinsPerDecadeMain": 66,
            "LogQBinsPerDecadeMidrange": 66,
            "LogQBinsPerDecadeWing": 66,
            "useLogQBinsDecadeCenter": False,
            "useLogQBinsEvenDecade": False,
            "sampleApertureSize": 14,
            "usePixelCalibration": True,
            "useTimeSlice": False,
            "timeSliceInterval": 10,
            "WedgeMinAngles": None,
            "WedgeMaxAngles": None,
            "autoWedgeQmin": 0.003,
            "autoWedgeQmax": 0.04,
            "autoWedgeQdelta": 0.01,
            "autoWedgePeakWidth": 0.5,
            "autoWedgeAzimuthalDelta": 1.0,
            "autoWedgeBackgroundWidth": 1.0,
            "autoWedgeSignalToNoiseMin": 2.0,
            "wedge1QminMain": 0.006,
            "wedge1QmaxMain": 0.15,
            "wedge1QminMidrange": 0.035,
            "wedge1QmaxMidrange": 0.225,
            "wedge1QminWing": 0.12,
            "wedge1QmaxWing": 1.0,
            "wedge1overlapStitchQmin": [0.05, 0.15],
            "wedge1overlapStitchQmax": [0.1, 0.2],
            "wedge2QminMain": 0.006,
            "wedge2QmaxMain": 0.15,
            "wedge2QminMidrange": 0.035,
            "wedge2QmaxMidrange": 0.225,
            "wedge2QminWing": 0.12,
            "wedge2QmaxWing": 1.0,
            "wedge2overlapStitchQmin": [0.05, 0.15],
            "wedge2overlapStitchQmax": [0.1, 0.2],
        }
    }
    refresh_cycle: int = 25

    @computed_field  # type: ignore
    @property
    def base_path(self) -> str:
        return f"/{self.facility}/{self.instrument}"

    @field_validator("wavelength", mode="before")
    @classmethod
    def validate_wavelength(cls, wavelength: str) -> Optional[float]:
        try:
            return float(wavelength)
        except (TypeError, ValueError):
            return None

    @field_validator("output_folder", mode="after")
    @classmethod
    def validate_output_folder(cls, output_folder: str) -> str:
        if not output_folder.startswith("/HFIR") and not output_folder.startswith("/SNS"):
            raise ValueError("The output folder must start with /HFIR or /SNS.")

        return output_folder

    @model_validator(mode="after")
    def update_wavelength(self) -> Self:
        self.common_configuration["configuration"]["wavelength"] = self.wavelength

        return self

    def update_configuration(self, options_only: bool = False) -> None:
        # Update the Instrument Configuration dropdown
        self.config_type_options = [
            self.create_config_type_option(option)
            for option in sorted(self.valid_configurations.get(self.run_cycle, {}).keys())
        ]
        if self.config_type_options and not any(
            option["value"] == self.config_type for option in self.config_type_options
        ):
            self.config_type = self.config_type_options[0]["value"]

        # Update the Sample Environment dropdown
        self.sample_env_options = sorted(
            self.valid_configurations.get(self.run_cycle, {}).get(self.config_type, {}).keys()
        )
        if self.sample_env_options and self.sample_env not in self.sample_env_options:
            self.sample_env = self.sample_env_options[0]

        if not options_only:
            # Try to update the drtsans configuration based on the users selected instrument inputs
            config_fname = (
                self.valid_configurations.get(self.run_cycle, {}).get(self.config_type, {}).get(self.sample_env, "")
            )
            if config_fname:
                self.config_path = f"{self.base_path}/shared/Cycle{self.run_cycle}/{config_fname}"
            self.update_config_type()
            self.update_flexible_pixelsizes()

    def reset(self) -> None:
        for field, field_info in self.model_fields.items():
            setattr(self, field, field_info.default)
        self.model_fields_set.clear()
        self.load_configurations()

    def get_config_type(self, distance: int, wavelength: int) -> int:
        if distance == 7 and wavelength == 6:
            return 2
        if distance == 15 and wavelength == 6:
            return 3
        if distance == 15 and wavelength == 12:
            return 4
        if distance == 15 and wavelength == 18:
            return 5

        return 0

    def create_config_type_option(self, option: int) -> dict[str, Any]:
        match option:
            case 2:
                return {"title": "7m, 6Å", "value": option}
            case 3:
                return {"title": "15m, 6Å", "value": option}
            case 4:
                return {"title": "15m, 12Å", "value": option}
            case 5:
                return {"title": "15m, 18Å", "value": option}
            case _:
                return {"title": "Unknown", "value": option}

    def parse_config_fname(self, fname: str) -> tuple[Optional[int], Optional[str]]:
        if fname.startswith("Intermediate"):
            config_type = 2
        elif fname.startswith("Long6A"):
            config_type = 3
        elif fname.startswith("Long12A"):
            config_type = 4
        elif fname.startswith("Long18A"):
            config_type = 5
        else:
            return (None, None)

        try:
            sample_env = fname.split("Config")[1].split("_")[0]
        except Exception:
            return (None, None)

        return (config_type, sample_env)

    def load_configurations(self) -> None:
        # The configurations are stored in the following format:
        # /HFIR/CG3/shared/Cycle{cycle_number}/{config_type}{sample_env}_RC{cycle_number}.txt
        try:
            for run_cycle in os.listdir(f"/{self.facility}/{self.instrument}/shared/"):
                try:
                    cycle_number = int(run_cycle.lstrip("Cycle"))
                    self.valid_configurations[cycle_number] = {}
                except ValueError:
                    continue

                for config_fname in os.listdir(f"/{self.facility}/{self.instrument}/shared/{run_cycle}"):
                    if str(cycle_number) not in config_fname:
                        continue

                    config_type, sample_env = self.parse_config_fname(config_fname)

                    if config_type is None or sample_env is None:
                        continue

                    if config_type not in self.valid_configurations[cycle_number]:
                        self.valid_configurations[cycle_number][config_type] = {}

                    self.valid_configurations[cycle_number][config_type][sample_env] = config_fname

            # Show most recent cycles first
            self.run_cycle_options = sorted(self.valid_configurations.keys(), reverse=True)

            # This allows new cycles to become the default without code change
            self.run_cycle = self.run_cycle_options[0]

            self.update_configuration()
        except OSError:
            logger.error("Analysis cluster filesystem not available, unable to load configuration")

    def load_old_config(self, config_data: str) -> dict[str, Any]:
        config_dict: dict[str, Any] = {}
        exec(config_data, {}, config_dict)

        self.ipts_number = config_dict.get("ipts_number", "")
        self.config_type = config_dict.get("Config", 2)
        self.sample_names = config_dict.get("sample_names", [])
        self.samples_thickness = config_dict.get("sample_thick", [])

        self.samples = config_dict.get("samples", [])
        self.samples_transmission = config_dict.get("samples_trans", [])
        self.backgrounds = config_dict.get("backgrounds", [])
        self.backgrounds_transmission = config_dict.get("backgrounds_trans", [])
        self.beam_center = config_dict.get("beam_center", None)
        self.empty_beam = config_dict.get("empty_trans", None)

        self.OL_range_Qmax = config_dict.get("OL_range_Qmax", [0.0, 1.0])
        self.OL_range_Qmin = config_dict.get("OL_range_Qmin", [0.0, 1.0])
        self.q_range_main = config_dict.get("q_range_main", [0.0, 1.0])
        self.q_range_midr = config_dict.get("q_range_midr", [0.0, 1.0])
        self.q_range_wing = config_dict.get("q_range_wing", [0.0, 1.0])
        self.refresh_cycle = config_dict.get("refreshCycle", 25)

        self.common_configuration = config_dict["common_configuration"]

        return config_dict

    def load_config(self, config_data: str) -> dict[str, Any]:
        try:
            config_dict = json.loads(config_data)

            for key in config_dict:
                if key != "common_configuration":
                    setattr(self, key, config_dict[key])
            if "common_configuration" in config_dict:
                self.common_configuration = config_dict["common_configuration"]
        except ValueError:
            config_dict = self.load_old_config(config_data)

        self.wavelength = self.common_configuration["configuration"]["wavelength"]

        self.update_configuration(options_only=True)

        return config_dict

    def prepare_config_file(self) -> str:
        return self.model_dump_json(
            exclude={
                "MAX_RANGES_NUM",
                "base_path",
                "ranges",
                "tool_id",
                "facility",
                "instrument",
                "can_add_range",
                "can_remove_range",
                "valid_configurations",
                "run_cycle_options",
                "config_type_options",
                "sample_env_options",
                "config_path",
                "wavelength",
            },
            indent=2,
        )

    def prepare_drtsans_config(self) -> List[dict]:
        configs = []
        for n in range(len(self.samples)):
            config = {
                "instrumentName": "CG3",
                "iptsNumber": self.ipts_number,
                "sample": {
                    "runNumber": self.samples[n],
                    "thickness": self.samples_thickness[n] if n < len(self.samples_thickness) else 1.0,
                    "transmission": {"runNumber": self.samples_transmission[n]}
                    if n < len(self.samples_transmission)
                    else {},
                },
                "background": {
                    "runNumber": self.backgrounds[n] if n < len(self.backgrounds) else "",
                    "transmission": {"runNumber": self.backgrounds_transmission[n]}
                    if n < len(self.backgrounds_transmission)
                    else {},
                },
                "beamCenter": {"runNumber": self.beam_center},
                "emptyTransmission": {"runNumber": self.empty_beam},
                "outputFileName": self.sample_names[n] if n < len(self.sample_names) else f"sample_{n}",
                "configuration": {
                    "outputDir": self.output_folder,
                    **self.common_configuration.get("configuration", {}),
                },
            }
            configs.append(config)
        return configs

    def set_samples(self, samples: List[Dict[str, Any]], index: Optional[int]) -> None:
        self.sample_names = [sample["name"] for sample in samples]
        self.stitching_sample = self.sample_names[0]

        self.samples = []
        self.samples_thickness = []
        for sample in samples:
            self.set_instrument_config(sample)

            self.samples.append(sample["name"])
            self.samples_thickness.append(sample["thickness"] / 10.0)

        self.samples = []
        self.samples_transmission = []
        for sample in samples:
            self.samples.append(",".join([str(run["run_number"]) for run in sample["runs"]]))
            transmission = ",".join([str(run["run_number"]) for run in sample["transmission"]])
            if not transmission:
                transmission = self.samples[-1]
            self.samples_transmission.append(transmission)

    def set_instrument_config(self, sample: Dict[str, Any]) -> None:
        run_cycle = sample.get("cycle_number", 0)
        if run_cycle:
            self.run_cycle = run_cycle

        distance = int(sample.get("distance", 0))
        wavelength = int(sample.get("wavelength", 0))
        config_type = self.get_config_type(distance, wavelength)
        if config_type:
            self.config_type = config_type

        self.update_configuration()

    def update_background(self) -> None:
        if self.background_sample:
            self.backgrounds = [str(run["run_number"]) for run in self.background_sample["runs"]]
            self.backgrounds_transmission = [str(run["run_number"]) for run in self.background_sample["transmission"]]
            if not self.backgrounds_transmission:
                self.backgrounds_transmission = self.backgrounds
            if not self.backgrounds:
                self.backgrounds = self.backgrounds_transmission

    def update_beam_center(self) -> None:
        if self.beam_center_sample:
            if self.beam_center_sample["runs"]:
                self.beam_center = str(self.beam_center_sample["runs"][0]["run_number"])
            elif self.beam_center_sample["transmission"]:
                self.beam_center = str(self.beam_center_sample["transmission"][0]["run_number"])
            else:
                self.beam_center = None

    def update_config_type(self) -> None:
        self.update_output_folder()

        if not self.config_path:
            return

        with open(self.config_path, "r") as _file:
            lines = _file.readlines()
            lambda_values = float(lines[2][:-1])
            if lambda_values >= 4.0 and lambda_values <= 25.0:
                self.common_configuration["configuration"]["wavelength"] = lambda_values
                self.wavelength = lambda_values

            lambda_spread = float(lines[3][:-1])
            if lambda_spread >= 7.0 and lambda_spread <= 45.0:
                self.common_configuration["configuration"]["wavelengthSpread"] = lambda_spread
                self.wavelength = lambda_values

            self.common_configuration["configuration"]["StandardAbsoluteScale"] = float(lines[4][:-1])

            mask_fname = lines[5][:-1]
            if not mask_fname.startswith("N"):
                self.common_configuration["configuration"]["maskFileName"] = mask_fname

            self.q_range_main = [float(lines[6][:-1]), float(lines[7][:-1])]
            self.q_range_midr = [float(lines[8][:-1]), float(lines[9][:-1])]
            self.q_range_wing = [float(lines[10][:-1]), float(lines[11][:-1])]
            self.OL_range_Qmin = [float(lines[12][:-1]), float(lines[14][:-1])]
            self.OL_range_Qmax = [float(lines[13][:-1]), float(lines[15][:-1])]
            self.stitching = [
                StitchingRange(min=self.OL_range_Qmin[0], max=self.OL_range_Qmax[0]),
                StitchingRange(min=self.OL_range_Qmin[1], max=self.OL_range_Qmax[1]),
            ]

            dark_mfname = lines[16][:-1]
            if not dark_mfname.startswith("N"):
                self.common_configuration["configuration"]["darkMainFileName"] = dark_mfname

            dark_wfname = lines[17][:-1]
            if not dark_wfname.startswith("N"):
                self.common_configuration["configuration"]["darkWingFileName"] = dark_wfname

            dark_mrfname = lines[18][:-1]
            if not dark_mrfname.startswith("N"):
                self.common_configuration["configuration"]["darkMidrangeFileName"] = dark_mrfname

            # TODO
            # shadow = lines[19][:-1]
            # wing_shadow = []
            # if not shadow.startswith("N"):
            #     wing_shadow = [{"Bank": shadow}]
            # self.common_configuration["configuration"]["defaultMask"] = wing_shadow

            sens_mrfname: Optional[str] = lines[20][:-1]
            if sens_mrfname and sens_mrfname.startswith("N"):
                sens_mrfname = None
            if self.flexible_pixelsizes:
                sens_mrfname = lines[21][:-1]
                if sens_mrfname and sens_mrfname.startswith("N"):
                    sens_mrfname = None
            self.common_configuration["configuration"]["sensitivityMidrangeFileName"] = sens_mrfname

            sens_wfname: Optional[str] = lines[22][:-1]
            if sens_wfname and sens_wfname.startswith("N"):
                sens_wfname = None
            if self.flexible_pixelsizes:
                sens_wfname = lines[23][:-1]
                if sens_wfname and sens_wfname.startswith("N"):
                    sens_wfname = None
            self.common_configuration["configuration"]["sensitivityWingFileName"] = sens_wfname

    def update_flexible_pixelsizes(self) -> None:
        # Typical format for the sensitivity file name: Sens_f{run_number}m6p3{sample_env}_WCL.nxs
        # [^r] prevents matching mid-range filenames that are otherwise very similar
        if self.flexible_pixelsizes:
            pattern = rf"Sens_f\d*m[^r].*{self.sample_env}_bs.*\.nxs"
        else:
            pattern = rf"Sens_f\d*m[^r].*{self.sample_env}_(?!bs).*\.nxs"

        main_sensitivity_fname = ""
        for fname in os.listdir(f"{self.base_path}/shared/Cycle{self.run_cycle}"):
            if re.match(pattern, fname):
                main_sensitivity_fname = f"{self.base_path}/shared/Cycle{self.run_cycle}/{fname}"

        self.common_configuration["configuration"]["sensitivityMainFileName"] = main_sensitivity_fname

    def update_empty_beam(self) -> None:
        if self.empty_beam_sample:
            if self.empty_beam_sample["runs"]:
                self.empty_beam = str(self.empty_beam_sample["runs"][0]["run_number"])
            elif self.empty_beam_sample["transmission"]:
                self.empty_beam = str(self.empty_beam_sample["transmission"][0]["run_number"])
            else:
                self.empty_beam = None

    def update_output_folder(self) -> None:
        self.output_folder = (
            f"{self.base_path}/IPTS-{self.ipts_number}/shared/"
            f"{getpass.getuser()}/RC{self.run_cycle}/Config{self.config_type}/"
        )

    def update_sample_selections(self, available_samples: Dict[int, str]) -> None:
        pass


class SharedConfig:
    """Config Singleton."""

    _instance = None

    def __new__(cls: Any, *args: Any, **kwargs: Any) -> Any:
        if cls._instance is None:
            cls._instance = BioSANSConfig()
            cls._instance.load_configurations()
        return cls._instance
