# Legacy Galaxy/NDIP integration — kept for reference only
# Not used in standalone mode
"""Galaxy classes."""

import argparse
import logging
import os
from typing import Any, Dict, List, Optional, Union

from nova.common.job import WorkState
from nova.galaxy import Connection, Dataset, DatasetCollection, Datastore, Parameters, Tool

from common.models.job import Job, job_states

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_job_state(job: Any) -> Optional[str]:
    for k, v in job["states"].items():
        if v == 1:
            return k
    return None


def parse_run_list(runs: Any) -> List:
    return []


class Galaxy:
    """Class that manages Galaxy connection."""

    def _parse_args(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--galaxy-url", help="URL of the Galaxy server")
        parser.add_argument("--galaxy-key", help="API key for accessing the Galaxy server")
        args, unknown = parser.parse_known_args()
        self.galaxy_url: Any = args.galaxy_url or os.getenv("GALAXY_URL")
        self.galaxy_api_key = args.galaxy_key or os.getenv("GALAXY_API_KEY")

    def __init__(self) -> None:
        self._parse_args()
        self.nova_connection = Connection(self.galaxy_url, self.galaxy_api_key).connect()
        self.store: Optional[Datastore] = None

    def ingest_datasets(self, config: Any, runs_to_register: List[Union[str, int]]) -> List[str]:
        n_files = len(runs_to_register)
        tool_params = Parameters()
        for i in range(n_files):
            fname = (
                f"/HFIR/{config.instrument}/{config.ipts_number}/nexus/{config.instrument}_{runs_to_register[i]}.nxs.h5"
            )
            tool_params.add_input(name=f"series_{i}|input", value=fname)

        ingest_tool = Tool(id="neutrons_register")

        outputs = ingest_tool.run(data_store=self.store, params=tool_params)
        return [output.id for output in outputs]

    def run_in_galaxy(self, config: Any, job: Job) -> None:
        self.store = self.nova_connection.get_data_store(name=f"IPTS-{config.ipts_number}")
        collections = self.run_reduction(config, job)
        job.reduction_complete = True
        self.export_results(config, job, collections)
        job.state_details = "reduction finished successfully"

    def export_results(self, config: Any, job: Job, collections: Any) -> None:
        job.state_details = f"exporting results to {config.output_folder}"

        tool_params = Parameters()
        for i, collection in enumerate(collections):
            tool_params.add_input(name=f"series_{i}|input_mode|input_mode_collection", value=True)
            tool_params.add_input(
                name=f"series_{i}|input_mode|export_folder", value=config.output_folder + collection["subfolder"]
            )
            tool_params.add_input(name=f"series_{i}|input_mode|input", value={"src": "hdca", "id": collection["id"]})

        if job.state != job_states.CANCELING:
            export_tool = Tool(id="neutrons_export")
            try:
                export_tool.run(data_store=self.store, params=tool_params)
            except Exception as e:
                raise Exception(export_tool.get_stderr(0, 1000000)) from e
        else:
            return

    def upload_file(self, file_path: str, config: Any, job: Job, name: str) -> Dict[str, Union[str, bool]]:
        try:
            result = Dataset(path=file_path, name=name)
            result.upload(store=self.store)

            tool_params = Parameters()
            tool_params.add_input(name="series_0|input_mode|input_mode_dataset", value=True)
            tool_params.add_input(name="series_0|input_mode|export_path", value=f"{config.output_folder}/{name}")
            tool_params.add_input(name="series_0|input_mode|input", value={"src": "hda", "id": result.id})

            export_tool = Tool(id="neutrons_export")
            export_tool.run(data_store=self.store, params=tool_params)

            return {"success": True}
        except Exception as e:
            logging.error(f"Error exporting file {name} from job {job.tool.id} to analysis cluster: {e}")
            return {"success": False, "error": str(e)}

    def run_reduction(self, config: Any, job: Job) -> List[Dict[str, str]]:
        # upload a file and wait until upload is finished
        job.state_details = "uploading configuration file to Galaxy"
        config_data = config.prepare_config_file()

        config_dataset = Dataset()
        config_dataset.set_content(config_data)
        ipts = config.ipts_number
        if ipts == "":
            raise Exception("ipts number not set")
        config_dataset.upload(self.store)
        config_id = config_dataset.id
        # params
        tool_params = Parameters()
        tool_params.add_input(name="ipts_number", value=int(ipts))
        tool_params.add_input(name="user_input", value={"src": "hda", "id": config_id})
        tool_params.add_input(name="staff_input", value={"src": "hda", "id": config_id})

        # run tool async but then wait for results
        job.state_details = "starting Galaxy tool"

        reduction_tool = Tool(id=config.tool_id)
        job.tool = reduction_tool
        if job.cancel:  # user canceled the job before it started
            job.cancel = False
            return []
        if job.state != job_states.CANCELING:
            reduction_tool.run(data_store=self.store, params=tool_params, wait=False)
            job.state_details = "waiting for data reduction to finish"
            reduction_tool.wait_for_results()
            outputs = reduction_tool.get_results()
            ids = []
            for output in outputs:
                ids.append(output.id)
        try:
            return [
                {"id": ids[0], "subfolder": ""},
                {"id": ids[1], "subfolder": "/1D"},
                {"id": ids[2], "subfolder": "/2D"},
            ]
        except Exception as e:
            raise Exception("Something went wrong with fetching the output of the data reduction.") from e

    def _get_collection_content(self, collection: DatasetCollection) -> List[Dict[str, str]]:
        elements = collection.get_content()
        results = []
        for elem in elements:
            name = elem["object"]["name"]
            root, ext = os.path.splitext(name)
            file_ext = elem["object"]["file_ext"]
            if ext != f".{file_ext}":
                name += f".{file_ext}"
            data_id = elem["object"]["id"]
            if file_ext in ["jpg", "png", "jpeg", "gif"]:
                filetype = "image"
            else:
                filetype = "text"
            results.append({"name": name, "id": data_id, "type": filetype})
        return results

    def get_job_results(self, job: Job) -> List[List[Dict[str, str]]]:
        outputs = job.tool.get_results()
        job.outputs = outputs
        results = []
        for o in outputs:
            if type(o) is DatasetCollection:
                results.append(self._get_collection_content(o))
        return results

    def get_dataset_content(self, dataset_id: str) -> bytes:
        # download dataset
        out = Dataset()
        out.id = dataset_id
        out.store = self.store
        return out.get_content()

    def get_job_outputs(self, job: Job) -> None:
        # stdout/stderr
        out_start = len(job.output)
        err_start = len(job.error)
        if not job.tool.get_uid():
            return
        try:
            output = job.tool.get_stdout(out_start, 1000000) or ""
            error = job.tool.get_stderr(err_start, 1000000) or ""
        except Exception as e:
            logger.error(e)
            output = ""
            error = ""

        if job.tool.get_status() == WorkState.RUNNING:
            job.output += output
            job.error += error
        else:
            job.output = output
            job.error = error

    def cancel_job(self, job: Job) -> None:
        if job.tool is None:
            # User canceled the job before it began, we need to interrupt the thread.
            job.cancel = True
        else:
            job.tool.cancel()


class SharedGalaxy:
    """Galaxy singleton."""

    _instance = None

    def __new__(cls: Any, *args: Any, **kwargs: Any) -> Any:
        if cls._instance is None:
            cls._instance = Galaxy(*args, **kwargs)
        return cls._instance
