"""Pydantic models shared between instruments."""

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


class NumberRange(BaseModel):
    """NumberRange validates min/max values for q-range and overlap min/max values."""

    max: float = 1.0
    min: float = 0.0

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.min >= self.max:
            raise ValueError("The start of the range must be less than the end of the range.")

        return self

    def reset(self) -> None:
        for field, field_info in self.model_fields.items():
            setattr(self, field, field_info.default)
        self.model_fields_set.clear()


class QRangeCleanCurves(NumberRange):
    """QRangeCleanCurves applies extra metadata to NumberRange."""

    max: float = Field(default=1.0, description="", examples=["0.1"])
    min: float = Field(default=0.0, description="", examples=["0.001"])


class StitchingRange(NumberRange):
    """StitchingRange applies extra metadata to NumberRange."""

    max: float = Field(
        default=1.0,
        description=(
            "This pair of parameters are to set the overlap range for stitching 1D data from two instrument "
            "configurations to produce a single curve. This is in addition to the merged curve from two detectors at "
            "one single configuration. The range is usually determined during the calibration, please consult your "
            "local contact if any change is desired."
        ),
        examples=["0.1"],
    )
    min: float = Field(
        default=0.0,
        description=(
            "This pair of parameters are to set the overlap range for stitching 1D data from two instrument "
            "configurations to produce a single curve. This is in addition to the merged curve from two detectors at "
            "one single configuration. The range is usually determined during the calibration, please consult your "
            "local contact if any change is desired."
        ),
        examples=["0.01"],
    )
