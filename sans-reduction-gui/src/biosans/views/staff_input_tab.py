"""Instrument inputs for staff/advanced users."""

from nova.trame.view.components import InputField
from nova.trame.view.layouts import GridLayout

from common.view_models.config import ConfigViewModel


class StaffInputTab:
    """Instrument inputs for staff/advanced users."""

    def __init__(self, config_view_model: ConfigViewModel) -> None:
        self.config_vm = config_view_model

        self.create_ui()

    def create_ui(self) -> None:
        with GridLayout(columns=3, classes="mb-2", gap="0.5em"):
            InputField(v_model="config.run_cycle", items="config.run_cycle_options", type="select")
            InputField(v_model="config.config_type", items="config.config_type_options", type="select")
            InputField(v_model="config.sample_env", items="config.sample_env_options", type="select")

        with GridLayout(columns=2, gap="0.5em"):
            InputField(v_model="config.wavelength")
            InputField(v_model="config.flexible_pixelsizes", type="checkbox")
