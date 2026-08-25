"""Calculate a two-point calibration from dry and field-capacity CSV logs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from calibration import (
    DatasetSummary,
    calculate_two_point_calibration,
    load_adc_values,
    resolve_dataset,
    summarize_dataset,
)


DEFAULT_DATA_DIRECTORY = Path(__file__).resolve().parent / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Map a dry reference to 0% and a field-capacity reference to 100%."
        )
    )
    parser.add_argument(
        "dry_reference",
        help="dry CSV path or timestamped filename prefix",
    )
    parser.add_argument(
        "field_capacity_reference",
        help="field-capacity CSV path or timestamped filename prefix",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIRECTORY,
        help=f"directory used to resolve prefixes (default: {DEFAULT_DATA_DIRECTORY})",
    )
    parser.add_argument(
        "--tail-samples",
        type=int,
        default=100,
        help="number of settled samples to use from the end of each file (default: 100)",
    )
    parser.add_argument(
        "--estimator",
        choices=("median", "mean"),
        default="median",
        help="endpoint estimator for the selected samples (default: median)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="optional JSON file for the calculated calibration",
    )
    return parser.parse_args()


def print_summary(label: str, summary: DatasetSummary) -> None:
    print(f"{label}: {summary.path}")
    print(
        f"  samples: {summary.selected_samples} selected from "
        f"{summary.total_samples} total"
    )
    print(
        f"  mean={summary.mean:.3f}, median={summary.median:.3f}, "
        f"std={summary.standard_deviation:.3f}, "
        f"range={summary.minimum}..{summary.maximum}"
    )
    print(f"  selected endpoint: {summary.endpoint:.3f}")


def main() -> int:
    args = parse_args()

    try:
        dry_path = resolve_dataset(args.dry_reference, args.data_dir)
        field_capacity_path = resolve_dataset(
            args.field_capacity_reference,
            args.data_dir,
        )
        dry_values = load_adc_values(dry_path)
        field_capacity_values = load_adc_values(field_capacity_path)
        dry_summary = summarize_dataset(
            dry_path,
            dry_values,
            args.tail_samples,
            args.estimator,
        )
        field_capacity_summary = summarize_dataset(
            field_capacity_path,
            field_capacity_values,
            args.tail_samples,
            args.estimator,
        )
        calibration = calculate_two_point_calibration(
            dry_summary.endpoint,
            field_capacity_summary.endpoint,
        )
    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"Calibration failed: {error}", file=sys.stderr)
        return 1

    print(f"Using the {args.estimator} of the final samples as each endpoint.\n")
    print_summary("Dry reference", dry_summary)
    print_summary("Field-capacity reference", field_capacity_summary)
    print("\nCalibration:")
    print(f"  ADC span: {calibration.adc_span:.3f}")
    print(
        "  relative_percent = clamp("
        f"{calibration.slope_percent_per_adc:.12f} * adc_raw "
        f"+ {calibration.intercept_percent:.12f}, 0, 100)"
    )
    print("  Reference table:")
    for percent in (0, 25, 50, 75, 100):
        print(
            f"    {percent:>3}% -> "
            f"ADC {calibration.adc_at_percent(percent):.1f}"
        )

    if args.output is not None:
        result = {
            "created_at": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
            "estimator": args.estimator,
            "tail_samples_requested": args.tail_samples,
            "dry_reference": dry_summary.to_dict(),
            "field_capacity_reference": field_capacity_summary.to_dict(),
            "calibration": calibration.to_dict(),
        }
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as error:
            print(f"Could not write {args.output}: {error}", file=sys.stderr)
            return 1
        print(f"\nSaved calibration to {args.output.resolve()}")

    print(
        "\nThis is a relative two-point scale, not absolute volumetric "
        "water content."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
