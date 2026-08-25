"""CSV logging helpers for timestamped ADC measurements."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import TextIO


INVALID_FILENAME_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def timestamped_csv_path(directory: Path, name: str) -> Path:
    """Build a safe CSV path with a local-clock timestamp after its name."""
    requested_name = Path(name).name
    if requested_name.lower().endswith(".csv"):
        requested_name = requested_name[:-4]

    safe_name = INVALID_FILENAME_CHARACTERS.sub("_", requested_name).strip(" .")
    if not safe_name:
        raise ValueError("CSV name must contain at least one valid character")

    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    return directory / f"{safe_name}_{timestamp}.csv"


def open_csv_log(path: Path) -> tuple[TextIO, csv.writer]:
    """Open an append-only CSV log and write its header when it is empty."""
    path.parent.mkdir(parents=True, exist_ok=True)
    is_empty = not path.exists() or path.stat().st_size == 0
    log_file = path.open("a", encoding="utf-8", newline="")
    writer = csv.writer(log_file)

    if is_empty:
        writer.writerow(("timestamp", "adc_filtered_raw"))
        log_file.flush()

    return log_file, writer


def log_reading(
    log_file: TextIO,
    writer: csv.writer,
    adc_filtered_raw: int,
) -> str:
    """Write one reading using the computer's local clock and return its timestamp."""
    timestamp = datetime.now().astimezone().isoformat(timespec="milliseconds")
    writer.writerow((timestamp, adc_filtered_raw))
    log_file.flush()
    return timestamp
