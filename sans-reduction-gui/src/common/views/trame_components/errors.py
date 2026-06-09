"""Trame components for showing errors in the GUI."""

from typing import Callable

from trame.widgets import html
from trame.widgets import vuetify3 as vuetify


class ErrorNotification:
    """Shows an error via a snackbar."""

    def __init__(self, v_model: str, message: str, close_callback: Callable) -> None:
        with vuetify.VSnackbar(
            v_model=v_model,
            color="error",
            multi_line=True,
        ):
            html.Span(message)

            with vuetify.Template(v_slot_actions=True):
                vuetify.VBtn("Close", click=close_callback)
