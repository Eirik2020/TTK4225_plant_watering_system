"""Print ESP32 ADC readings received over its USB serial connection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import serial

from csv_logger import log_reading, open_csv_log, timestamped_csv_path
from serial_usb import available_ports, open_serial, parse_adc_reading


DEFAULT_LOG_DIRECTORY = Path(__file__).resolve().parent / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read ADC samples printed by the ESP32 firmware."
    )
    parser.add_argument(
        "csv_name",
        nargs="?",
        default="adc_readings",
        help="CSV file name before the automatically added timestamp",
    )
    parser.add_argument(
        "--port",
        default="COM8",
        help="serial port connected to the ESP32 (default: COM8)",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=115_200,
        help="serial baud rate (default: 115200)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="print every non-empty firmware line, not only ADC readings",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_LOG_DIRECTORY,
        help=f"CSV output directory (default: {DEFAULT_LOG_DIRECTORY})",
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="list detected serial ports and exit",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.list_ports:
        print(available_ports())
        return 0

    try:
        output_path = timestamped_csv_path(args.output_dir, args.csv_name)
    except ValueError as error:
        print(f"Invalid CSV name: {error}", file=sys.stderr)
        return 2

    try:
        with open_serial(args.port, args.baudrate) as connection:
            log_file, log_writer = open_csv_log(output_path)
            with log_file:
                print(
                    f"Listening for ADC readings on {args.port} at "
                    f"{args.baudrate} baud."
                )
                print(f"Logging samples to {output_path.resolve()}.")
                print("Press Ctrl+C to stop.")

                while True:
                    data = connection.readline()
                    if not data:
                        continue

                    line = data.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue

                    adc_raw = parse_adc_reading(line)
                    if adc_raw is not None:
                        timestamp = log_reading(log_file, log_writer, adc_raw)
                        print(
                            f"{timestamp} | Filtered ADC raw value: {adc_raw}",
                            flush=True,
                        )
                    elif args.all:
                        print(line, flush=True)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    except serial.SerialException as error:
        print(f"Could not open or read {args.port}: {error}", file=sys.stderr)
        print(
            "Close espflash/LaTeX monitors or other programs using the port.\n"
            "Detected serial ports:\n"
            f"{available_ports()}",
            file=sys.stderr,
        )
        return 1
    except OSError as error:
        print(f"Could not write CSV log {output_path}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
