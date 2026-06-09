"""Local drtsans reduction — drop-in replacement for Galaxy."""

import json
import logging
import os
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any

from common.models.job import Job, job_states

logger = logging.getLogger(__name__)

SANS_PYTHON = "/usr/local/pixi/sans/.pixi/envs/default/bin/python"
_WORKER = Path(__file__).resolve().parent / "reduction_worker.py"
_INSTRUMENT_MAP = {"CG2": "GPSANS", "CG3": "BIOSANS"}


class LocalReduction:
    """Runs drtsans reduction locally, replacing Galaxy."""

    def __init__(self) -> None:
        self._cancel_event = threading.Event()
        self.galaxy_url = ""  # not needed for standalone
        self._output_folder = ""

    def run_reduction(self, config: Any, job: Job) -> None:
        """Main entry point — replaces Galaxy.run_in_galaxy()"""
        self._cancel_event.clear()
        self._output_folder = getattr(config, "output_folder", "")
        instrument = getattr(config, "instrument", "")
        drtsans_configs = config.prepare_drtsans_config()

        job.state_details = f"starting local reduction for {len(drtsans_configs)} sample(s)"

        for i, drtsans_dict in enumerate(drtsans_configs):
            if self._cancel_event.is_set() or job.state == job_states.CANCELING:
                job.state_details = "reduction cancelled"
                return

            job.state_details = f"reducing sample {i + 1} of {len(drtsans_configs)}"

            try:
                if instrument == "CG3":  # BioSANS
                    self._run_biosans(drtsans_dict, job)
                else:  # GPSANS CG2
                    self._run_gpsans(drtsans_dict, job)
            except Exception as e:
                job.error += f"\nSample {i + 1} failed: {str(e)}"
                logger.error(f"Reduction failed for sample {i + 1}: {e}")
                raise

        job.reduction_complete = True
        job.state_details = "reduction finished successfully"

    def _run_biosans(self, drtsans_dict: dict, job: Job) -> None:
        self._run_subprocess(drtsans_dict, "CG3", job)

    def _run_gpsans(self, drtsans_dict: dict, job: Job) -> None:
        self._run_subprocess(drtsans_dict, "CG2", job)

    def _run_subprocess(self, drtsans_dict: dict, instrument: str, job: Job) -> None:
        fd, config_path = tempfile.mkstemp(suffix=".json")
        try:
            mapped = dict(drtsans_dict)
            mapped["instrumentName"] = _INSTRUMENT_MAP.get(mapped.get("instrumentName", ""), mapped.get("instrumentName", ""))
            with os.fdopen(fd, "w") as f:
                json.dump(mapped, f)

            proc = subprocess.Popen(
                [SANS_PYTHON, str(_WORKER), config_path, instrument],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            def _stream_stdout() -> None:
                for line in proc.stdout:
                    job.output += f"\n{line.rstrip()}"

            def _stream_stderr() -> None:
                for line in proc.stderr:
                    job.error += f"\n{line.rstrip()}"

            t_out = threading.Thread(target=_stream_stdout, daemon=True)
            t_err = threading.Thread(target=_stream_stderr, daemon=True)
            t_out.start()
            t_err.start()
            proc.wait()
            t_out.join()
            t_err.join()

            if proc.returncode != 0:
                raise RuntimeError(f"reduction worker exited with code {proc.returncode}")
        finally:
            os.unlink(config_path)

    def get_job_outputs(self, job: Job) -> None:
        pass  # output is written directly to job.output during reduction

    def get_job_results(self, config: Any):
        output_folder = getattr(config, "output_folder", "")
        output_path = Path(output_folder) if output_folder else None
        if not output_path or not output_path.is_dir():
            return [[], [], []]

        def _scan(directory: Path, patterns: list) -> list:
            if not directory.is_dir():
                return []
            files = []
            for pattern in patterns:
                for fpath in sorted(directory.glob(pattern)):
                    if fpath.is_file():
                        ftype = "image" if fpath.suffix.lower() in (".png", ".jpg", ".jpeg") else "text"
                        files.append({"name": fpath.name, "id": str(fpath), "type": ftype})
            return files

        h5_files = []
        for pattern in ("*.h5", "*.hdf"):
            for fpath in sorted(output_path.glob(pattern)):
                if fpath.is_file():
                    h5_files.append({"name": fpath.name, "id": str(fpath), "type": "h5"})

        return [
            h5_files,
            _scan(output_path / "1D", ["*.txt", "*.dat", "*.png"]),
            _scan(output_path / "2D", ["*.dat", "*.png"]),
        ]

    def get_dataset_content(self, dataset_id: Any) -> bytes:
        try:
            return Path(dataset_id).read_bytes()
        except Exception:
            return b""

    def upload_file(self, iqmod_fname: Any, config: Any, job: Job, export_fname: str) -> None:
        return None  # not needed for standalone

    def cancel_job(self, job: Job) -> None:
        self._cancel_event.set()
        if hasattr(job, "tool") and job.tool is not None:
            try:
                job.tool.cancel()
            except Exception:
                pass


class SharedLocalReduction:
    """Drop-in singleton replacement for SharedGalaxy."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = LocalReduction(*args, **kwargs)
        return cls._instance
