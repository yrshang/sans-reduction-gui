"""Init."""

from typing import Any


class DictObject(dict):
    """Dict object."""

    def __getattr__(self, key: Any) -> Any:
        """Getter."""
        try:
            return self[key]
        except KeyError as err:
            raise AttributeError(key) from err

    def __setattr__(self, key: Any, value: Any) -> None:
        """Setter."""
        self[key] = value

    pass
