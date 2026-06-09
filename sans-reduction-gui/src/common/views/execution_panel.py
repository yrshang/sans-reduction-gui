"""Defines the execution controls at the bottom of the application."""

from typing import Any, Optional

from trame.widgets import client, html
from trame.widgets import vuetify3 as vuetify

from common.view_models.execution import ExecutionViewModel
from common.views.trame_components.errors import ErrorNotification


class ExecutionPanel:
    """Execution panel."""

    def __init__(self, server: Any, view_model: ExecutionViewModel) -> None:
        self.server = server
        self.state = server.state
        self.ctrl = server.controller

        self.view_model = view_model
        self.view_model.buttons_state_bind.connect()
        self.view_model.view_state_bind.connect("execution")

        self.view_model.confirm_dialog_message_bind.connect("confirm_dialog_messages")
        self.view_model.show_confirm_dialog_bind.connect("confirm_dialog")
        self.view_model.error_dialog_message_bind.connect("error_dialog_message")
        self.view_model.show_error_dialog_bind.connect("error_dialog")
        self.view_model.skip_confirmation_bind.connect("skip_confirmation")

        # TODO: This whole mechanism isn't necessary if we can detect required fields with Pydantic
        self.reset_form = client.JSEval(
            exec="window.setTimeout(() => { trame.refs.form.resetValidation(); }, 250)"
        ).exec
        self.view_model.reset_form_bind.connect(self.reset_form)

        self.create_ui()
        self.view_model.update_view()

    def create_ui(self) -> None:
        ErrorNotification(
            "execution.upload_failed",
            "Failed to upload config: {{ execution.upload_error }}",
            self.view_model.clear_error,
        )

        with html.Div(classes="d-flex justify-center my-4 w-100"):
            vuetify.VBtn(
                "Reset Config",
                v_if=("!config_btn_disabled",),
                classes="mr-2",
                prepend_icon="mdi-reload",
                click="window.confirm('This will fully reset the configuration and remove any results from the "
                "application. Are you sure you want to proceed?') ? trigger('reset_config') : '';",
            )
            vuetify.VFileInput(
                v_model=("config_file", None),
                classes="d-none",
                ref="fread",
            )
            vuetify.VBtn(
                "Upload Config",
                v_if=("!config_btn_disabled",),
                classes="mr-2",
                prepend_icon="mdi-upload",
                click="skip_confirmation || window.confirm('This will remove your current results from the "
                "application. Are you sure you want to proceed?') ? trame.refs.fread.click() : '';",
            )
            vuetify.VBtn(
                "Download Config",
                v_if=("!config_btn_disabled",),
                prepend_icon="mdi-file-download",
                click=(
                    "trigger('download_config').then((data) => {"
                    "  console.log(data);"
                    "  if (data !== null) {"
                    "    utils.download('sans_config.json', data, 'application/json')"
                    "  };"
                    "})"
                ),
            )
            vuetify.VDivider(v_if="!config_btn_disabled", classes="mx-8", thickness=2, vertical=True)
            vuetify.VBtn(
                "Run",
                v_if=("!run_btn_disabled",),
                prepend_icon="mdi-play",
                click=self.run,
            )
            vuetify.VBtn(
                "Cancel",
                v_if=("!cancel_btn_disabled",),
                color="error",
                prepend_icon="mdi-stop",
                click=self.cancel,
            )

        with vuetify.VDialog(v_model="confirm_dialog", width="auto"):
            with vuetify.VCard(width=600):
                vuetify.VCardTitle("Run Confirmation")
                with vuetify.VCardText():
                    with html.Div(v_for="message in confirm_dialog_messages", classes="mb-2"):
                        vuetify.VAlert(v_if="message.type === 'warning'", text=("message.text",), type="warning")
                        html.P(v_else=True, v_text=("message.text",), classes="text-center")
                with vuetify.VCardActions():
                    vuetify.VBtn("Cancel", click="confirm_dialog = False", size="small", color="error")
                    vuetify.VBtn("Run", click=self.view_model.run_with_overwrite, size="small", color="primary")

        with vuetify.VDialog(v_model="error_dialog", width="auto"):
            with vuetify.VCard(classes="text-center", text=("error_dialog_message",)):
                with vuetify.VCardActions():
                    vuetify.VBtn("Close", block=True, click="error_dialog = False", size="small", color="primary")

        @self.state.change("config_file")
        def read_config_file(config_file: Any, **_kwargs: Any) -> None:
            if config_file is None:
                return
            config_data = config_file["content"].decode("utf-8")
            # set config before call to view_model, otherwise we get inifinite loop
            self.state.config_file = None
            self.view_model.load_config(config_data)

        @self.ctrl.trigger("download_config")
        def generate_content() -> Optional[str]:
            return self.view_model.prepare_config_file()

        @self.ctrl.trigger("reset_config")
        def reset() -> None:
            self.view_model.reset_config()

    def run(self) -> None:
        self.view_model.run()

    def cancel(self) -> None:
        self.view_model.cancel()
