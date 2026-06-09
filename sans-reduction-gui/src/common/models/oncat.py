"""Top level of ONCat model."""

import logging
import os
from typing import Any, Dict, List, Optional

try:
    from mantid.simpleapi import Integration, Load
except ImportError:
    pass
from numpy import arange, log, ma, transpose
import pyoncat

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ONCatModel:
    """Oncat model."""

    CHART_MARGIN = 50

    def __init__(self, facility: str, instrument: str) -> None:
        # State for running ONCat
        self.error = False
        self.facility = facility
        self.instrument = instrument

        token_store = pyoncat.FileSystemTokenStore(
            os.path.expanduser("~/.oncat_token.json")
        )
        self.oncat_params = dict(
            client_id="eaeb036a-2602-4bb9-8530-0bb5812da7a1",
            scopes=["api:read", "data:read", "openid"],
            token_getter=token_store.read_token,
            token_setter=token_store.write_token,
            flow=pyoncat.DEVICE_AUTHORIZATION_FLOW,
        )

        self.current_experiment = None
        self.client = None

    def _oncat(self, resource: Any, action: Any, *args: Any, **kwargs: Any) -> Any:
        if self.client is None:
            try:
                self.client = pyoncat.ONCat("https://oncat.ornl.gov", **self.oncat_params)
            except Exception as e:
                self.error = True
                logging.error(f"Failed to connect to ONCat: {e}")
                self.client = None
        try:
            result = getattr(getattr(self.client, resource), action)(*args, **kwargs)
            self.error = False
            return result
        except Exception as e:
            self.error = True
            logging.error(f"Failed to query ONCat: {e}")
            if action == "list":
                return []
            # More actions can be supported here if needed in the future
            return None

    def _parse_enum(self, enum_obj: dict[str, Any]) -> str:
        index = round(enum_obj.get("average_value", 0))
        options = enum_obj.get("enum", {}).get("names", [])
        if len(options) <= index:
            value = ""
        else:
            value = options[index]
        return value.strip()

    def _parse_datafile_metadata(self, datafile: Any) -> dict[str, Any]:
        attenuator_obj = datafile.get("metadata", {}).get("entry", {}).get("daslogs", {}).get("attenuator", {})
        guides_obj = datafile.get("metadata", {}).get("entry", {}).get("daslogs", {}).get("nguides", {})
        location = datafile.get("location", None)
        run_number = datafile.get("indexed", {}).get("run_number", None)

        # The attenuator and nguides are stored as integer indices into a list of options
        attenuator = self._parse_enum(attenuator_obj)
        guides = self._parse_enum(guides_obj)

        # These numbers are rounded due to each being a very long floating point value
        cycle_number = datafile.get("metadata", {}).get("entry", {}).get("daslogs", {}).get("cycle_number", {})
        cycle_number = round(cycle_number.average_value) if cycle_number else 0
        distance = datafile.get("metadata", {}).get("entry", {}).get("daslogs", {}).get("sample_detector_distance", {})
        distance = round(distance.average_value, 1) if distance else 0.0
        thickness = datafile.get("metadata", {}).get("entry", {}).get("daslogs", {}).get("sample_thickness", {})
        thickness = round(thickness.average_value, 3) if thickness else 0.0
        wavelength = datafile.get("metadata", {}).get("entry", {}).get("daslogs", {}).get("wavelength", {})
        wavelength = round(wavelength.average_value) if wavelength else 0

        title = datafile.get("metadata", {}).get("entry", {}).get("title", "")
        sample_name = ""
        if title and "smpl:" in title:
            sample_name = f"{title.split('smpl:')[1].strip()} ({distance}m, {wavelength}Å)"

        return {
            "attenuator": attenuator,
            "cycle_number": cycle_number,
            "distance": distance,
            "guides": guides,
            "location": location,
            "run_number": run_number,
            "sample_name": sample_name,
            "thickness": thickness,
            "title": title,
            "wavelength": wavelength,
        }

    def needs_login(self) -> bool:
        token_path = os.path.expanduser("~/.oncat_token.json")
        if not os.path.exists(token_path):
            return True
        return os.path.getsize(token_path) == 0

    def get_error_state(self) -> bool:
        return self.error

    def get_experiments(self) -> List[Dict[str, str]]:
        experiments = self._oncat(
            "Experiment",
            "list",
            facility=self.facility,
            instrument=self.instrument,
            projection=["open", "title"],
        )

        return sorted(
            [
                {
                    "title": f"{experiment.get('id', '')} - {experiment.get('title', '')}",
                    "value": experiment.get("id", "").split("-")[-1],
                }
                for experiment in experiments
            ],
            key=lambda x: int(x["value"]),
            reverse=True,
        )

    def get_preview(self, run: dict[str, Any]) -> dict[str, Any]:
        location = run["location"]
        try:
            workspace = Load(location)
            integrated_workspace = Integration(workspace)
            x = arange(192) + 1
            y = arange(256) + 1
            # extractY retrieves the data from the workspace
            # The rest aligns the data with our x and y bins
            data = integrated_workspace.extractY().reshape(-1, 8, 256).T
            data = data[:, [0, 4, 1, 5, 2, 6, 3, 7], :].transpose().reshape(-1, 256)
            # Mask small values and take the log of the data before plotting
            z = transpose(ma.masked_where(data < 1, data))
            z = log(z, where=z > 0)

            y_axis = workspace.getAxis(1).getUnit()

            return {
                "heatmap": {
                    "data": [
                        {
                            "x": x.tolist(),
                            "y": y.tolist(),
                            "z": z.tolist(),
                            "type": "heatmap",
                            "colorbar": {"title": y_axis.caption()},
                            "colorscale": "Viridis",
                        }
                    ],
                    "layout": {
                        "margin": {
                            "b": self.CHART_MARGIN,
                            "l": self.CHART_MARGIN,
                            "r": self.CHART_MARGIN,
                        },
                        "title": os.path.basename(location),
                        "xaxis": {"fixedrange": True, "title": "Tube"},
                        "yaxis": {"fixedrange": True, "title": "Pixel"},
                        "height": 300,
                        "width": 300,
                    },
                },
                "location": location,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_run_number(self, run_number: str) -> Optional[dict[str, Any]]:
        run_data = self._oncat(
            "Run",
            "list",
            facility=self.facility,
            instrument=self.instrument,
            ranges=run_number,
            projection=["datafiles.raw.location", "experiment"],
        )

        if not run_data:
            return None

        experiment = run_data[0].get("experiment", None)
        location = run_data[0].get("datafiles", {}).get("raw", {}).get("location", "")

        if not experiment or not location or not os.access(location, os.R_OK):
            return None

        # Query ONCat for relevant metadata to display to the user
        datafile = self._oncat(
            "Datafile",
            "retrieve",
            location,
            facility=self.facility,
            instrument=self.instrument,
            experiment=experiment,
            projection=[
                "indexed.run_number",
                "metadata.entry.daslogs.attenuator",
                "metadata.entry.daslogs.sample_detector_distance",
                "metadata.entry.daslogs.sample_thickness",
                "metadata.entry.daslogs.wavelength",
                "metadata.entry.title",
            ],
        )

        if not datafile:
            return None

        metadata = self._parse_datafile_metadata(datafile)
        if metadata["sample_name"]:
            return {
                "distance": metadata["distance"],
                "name": f"From {experiment}: {metadata['sample_name']}",
                "thickness": metadata["thickness"],
                "runs": [
                    {
                        "run_number": metadata["run_number"],
                        "location": metadata["location"],
                        "title": metadata["title"],
                    }
                ],
                "transmission": [],
                "wavelength": metadata["wavelength"],
            }

        return None

    def get_samples(self, ipts_number: str) -> dict[str, Any]:
        samples = {}
        for datafile in self._oncat(
            "Datafile",
            "list",
            facility=self.facility,
            instrument=self.instrument,
            experiment=f"IPTS-{ipts_number}",
            projection=[
                "indexed.run_number",
                "metadata.entry.daslogs.attenuator",
                "metadata.entry.daslogs.cycle_number",
                "metadata.entry.daslogs.nguides",
                "metadata.entry.daslogs.sample_detector_distance",
                "metadata.entry.daslogs.sample_thickness",
                "metadata.entry.daslogs.wavelength",
                "metadata.entry.title",
            ],
        ):
            metadata = self._parse_datafile_metadata(datafile)
            if metadata["attenuator"] is None:
                continue

            if metadata["sample_name"] not in samples:
                samples[metadata["sample_name"]] = {
                    "attenuator": metadata["attenuator"],
                    "cycle_number": metadata["cycle_number"],
                    "distance": metadata["distance"],
                    "guides": metadata["guides"],
                    "name": metadata["sample_name"],
                    "thickness": metadata["thickness"],
                    "runs": [],
                    "transmission": [],
                    "wavelength": metadata["wavelength"],
                }

                if metadata["attenuator"] == "Open":
                    samples[metadata["sample_name"]]["runs"].append(
                        {
                            "run_number": metadata["run_number"],
                            "location": metadata["location"],
                            "title": metadata["title"],
                        }
                    )
                else:
                    samples[metadata["sample_name"]]["transmission"].append(
                        {
                            "run_number": metadata["run_number"],
                            "location": metadata["location"],
                            "title": metadata["title"],
                        }
                    )

        return samples


class SharedONCat:
    """ONCat singleton."""

    _instance = None

    def __new__(cls: Any, *args: Any, **kwargs: Any) -> Any:
        if cls._instance is None:
            cls._instance = ONCatModel(*args, **kwargs)
        return cls._instance
