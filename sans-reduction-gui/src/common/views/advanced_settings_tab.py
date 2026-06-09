"""Advanced Settings Tab."""

from typing import Any, Union

from trame.widgets import vuetify3 as vuetify


class AdvancedSettingsTab:
    """Advanced Settings Tab."""

    def __init__(self, server: Any, viewmodel: Any) -> None:
        self.view_model = viewmodel
        self.view_model.text_config_bind.connect("")
        self.ctrl = server.controller
        self.create_ui()

    def on_change(self) -> None:
        self.view_model.text_config_updated()

    def create_ui(self) -> None:
        vuetify.VTextarea(
            v_model="text_config",
            no_resize=True,
            variant="outlined",
            __events=["change"],
            change=self.on_change,
            rules=("[(v) => trigger('validate_text_config', [v])]",),
        )

        @self.ctrl.trigger("validate_text_config")
        def validate_text_config(value: Any) -> Union[bool, str]:
            return self.view_model.validate_text_config(value)
