"""Exceptions for the SANS GUI."""

from typing import Any


class ConfigError(Exception):
    """Handle exceptions when loading configuration files."""

    def __init__(self, cause: Any) -> None:
        self.cause = cause

    def __str__(self) -> str:
        """Display error as string."""
        return repr(self.cause)
