"""Jobs."""

import types
from typing import Any, Optional


job_states = types.SimpleNamespace()


job_states.NONE = "not started"
job_states.RUNNING = "running"
job_states.FINISHED_OK = "finished ok"
job_states.FAILED = "failed"
job_states.CANCELED = "canceled"
job_states.CANCELING = "canceling"


class Job:
    """Job class."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.state = job_states.NONE
        self.state_details = ""
        self.cancel = False
        self.error = ""
        self.output = ""
        self.reduction_complete = False
        self.config_id = ""
        self.results: Any = None
        self.tool: Any = None
        self.outputs: Optional[Any] = None


class SharedJob:
    """Job singleton."""

    _instance = None

    def __new__(cls: Any, *args: Any, **kwargs: Any) -> Any:
        if cls._instance is None:
            cls._instance = Job()
        return cls._instance
