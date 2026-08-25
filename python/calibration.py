"""Calculations for two-point soil-moisture sensor calibration."""

from __future__ import annotations

import csv
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path


ADC_COLUMNS = ("adc_filtered_raw", "adc_raw")


@dataclass(frozen=True)
class DatasetSummary:
    path: str
    total_samples: int
    selected_samples: int
    mean: float
    median: float
    standard_deviation: float
    minimum: int
    maximum: int
    endpoint: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class TwoPointCalibration:
    dry_adc: float
    field_capacity_adc: float
    adc_span: float
    slope_percent_per_adc: float
    intercept_percent: float

    def relative_percent(self, adc_raw: float, *, clamp: bool = True) -> float:
        """Map an ADC reading to the dry=0%, field-capacity=100% scale."""
        percent = self.slope_percent_per_adc * adc_raw + self.intercept_percent
        if clamp:
            return min(100.0, max(0.0, percent))
        return percent

    def adc_at_percent(self, percent: float) -> float:
        """Return the raw ADC value corresponding to a relative percentage."""
        return (percent - self.intercept_percent) / self.slope_percent_per_adc

    def to_dict(self) -> dict[str, float | str]:
        return {
            **asdict(self),
            "scale": "dry reference = 0%, field capacity reference = 100%",
        }


def resolve_dataset(reference: str, data_directory: Path) -> Path:
    """Resolve a CSV path or the newest timestamped file matching a prefix."""
    requested = Path(reference)
    direct_candidates = (requested, data_directory / requested)

    for candidate in direct_candidates:
        if candidate.is_file():
            return candidate.resolve()

    prefix = requested.stem
    matches = [
        path
        for path in data_directory.glob("*.csv")
        if path.stem == prefix or path.stem.startswith(f"{prefix}_")
    ]
    if not matches:
        raise FileNotFoundError(
            f"No CSV file matching {reference!r} in {data_directory.resolve()}"
        )

    return max(matches, key=lambda path: path.stat().st_mtime).resolve()


def load_adc_values(path: Path) -> list[int]:
    """Read filtered ADC values from a logger-generated CSV file."""
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames or []
        value_column = next(
            (column for column in ADC_COLUMNS if column in fieldnames),
            None,
        )
        if value_column is None:
            expected = " or ".join(repr(column) for column in ADC_COLUMNS)
            raise ValueError(f"{path} must contain a {expected} column")

        values: list[int] = []
        for line_number, row in enumerate(reader, start=2):
            raw_value = row.get(value_column, "")
            try:
                values.append(int(raw_value))
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid ADC value {raw_value!r} in {path} line {line_number}"
                ) from error

    if not values:
        raise ValueError(f"{path} contains no ADC samples")

    return values


def summarize_dataset(
    path: Path,
    values: list[int],
    tail_samples: int,
    estimator: str,
) -> DatasetSummary:
    """Summarize the selected settled portion of a reference dataset."""
    if tail_samples < 1:
        raise ValueError("tail_samples must be at least 1")

    selected = values[-tail_samples:]
    mean = statistics.fmean(selected)
    median = float(statistics.median(selected))
    endpoint = median if estimator == "median" else mean
    standard_deviation = (
        statistics.stdev(selected) if len(selected) > 1 else 0.0
    )

    return DatasetSummary(
        path=str(path),
        total_samples=len(values),
        selected_samples=len(selected),
        mean=mean,
        median=median,
        standard_deviation=standard_deviation,
        minimum=min(selected),
        maximum=max(selected),
        endpoint=endpoint,
    )


def calculate_two_point_calibration(
    dry_adc: float,
    field_capacity_adc: float,
) -> TwoPointCalibration:
    """Calculate a linear dry=0%, field-capacity=100% mapping."""
    adc_span = field_capacity_adc - dry_adc
    if adc_span == 0:
        raise ValueError("Dry and field-capacity ADC endpoints must differ")

    slope = 100.0 / adc_span
    intercept = -dry_adc * slope
    return TwoPointCalibration(
        dry_adc=dry_adc,
        field_capacity_adc=field_capacity_adc,
        adc_span=abs(adc_span),
        slope_percent_per_adc=slope,
        intercept_percent=intercept,
    )
