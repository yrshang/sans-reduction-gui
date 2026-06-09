"""General trame components."""

from typing import Any

from nova.trame.view.components import InputField
from trame.widgets import vuetify3 as vuetify


class NumberRange:
    """Number range."""

    def __init__(
        self,
        models: Any,
        labels: Any,
        **kwargs: Any,
    ) -> None:
        if isinstance(labels, tuple) or isinstance(labels, str):
            labels = [labels]

        with vuetify.VContainer(classes="align-start d-flex justify-space-between ma-0 pa-0", fluid=True):
            InputField(
                v_model=models[0],
                classes="w-50",
                label=labels[0],
                **kwargs,
            )
            vuetify.VLabel("-", classes="px-1", style={"margin-top": "1.6em"})
            InputField(
                v_model=models[1],
                classes="w-50",
                label=labels[1] if len(labels) > 1 else labels[0],
                **kwargs,
            )
