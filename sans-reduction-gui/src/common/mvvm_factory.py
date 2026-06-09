"""Instantiates view models for Trame binding."""

from typing import Any, Dict

from common.models.main import MainModel
from common.view_models.config import ConfigViewModel
from common.view_models.execution import ExecutionViewModel
from common.view_models.job_outputs import JobOutputsViewModel
from common.view_models.job_results import JobResultsViewModel
from common.view_models.main import MainViewModel
from common.view_models.oncat import ONCatViewModel
from common.view_models.stitching import StitchingViewModel


def create_viewmodels(config_class: Any, binding: Any, args: Any) -> Dict[str, Any]:
    model = MainModel(config_class, args)
    vm: Dict[str, Any] = {}
    vm["main"] = MainViewModel(model, binding, args)
    vm["oncat"] = ONCatViewModel(model, binding)
    vm["stitching"] = StitchingViewModel(model, binding)
    vm["config"] = ConfigViewModel(model, vm["oncat"], vm["stitching"], binding)
    vm["job_outputs"] = JobOutputsViewModel(model, binding)
    vm["job_results"] = JobResultsViewModel(model, binding)
    vm["execution"] = ExecutionViewModel(
        model=model,
        outputs_vm=vm["job_outputs"],
        config_vm=vm["config"],
        results_vm=vm["job_results"],
        oncat_vm=vm["oncat"],
        stitching_vm=vm["stitching"],
        binding=binding,
    )

    return vm
