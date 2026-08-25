"""Helpers for reading ADC output from the ESP32 USB-to-UART connection."""

from __future__ import annotations

import re

import serial
from serial.tools import list_ports


ADC_READING = re.compile(r"MOISTURE filtered_raw=(\d+)")


def available_ports() -> str:
    """Return a human-readable list of detected serial ports."""
    ports = list(list_ports.comports())
    if not ports:
        return "  No serial ports detected."

    return "\n".join(
        f"  {port.device}: {port.description}" for port in ports
    )


def open_serial(port: str, baudrate: int) -> serial.Serial:
    """Open a port without asserting the ESP32 reset/boot control lines."""
    connection = serial.Serial()
    connection.port = port
    connection.baudrate = baudrate
    connection.timeout = 1
    connection.dtr = False
    connection.rts = False
    connection.open()
    return connection


def parse_adc_reading(line: str) -> int | None:
    """Extract an integer ADC value from one firmware output line."""
    match = ADC_READING.search(line)
    if match is None:
        return None

    return int(match.group(1))
