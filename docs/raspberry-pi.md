# Raspberry Pi measurement logger

This guide reproduces the Raspberry Pi setup used to record filtered ESP32
soil-moisture measurements over USB. The logger runs as a systemd template
service, restarts after serial failures, starts at boot when enabled, and
writes timestamped CSV files under `python/data/`.

The examples use the account and hostname `ferropi@ferropi.local`. Replace
them if the Pi has a different user or hostname.

## 1. Prepare a fresh Pi

Install Git and Python virtual-environment support:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv
```

Clone the repository as the normal, non-root Pi user:

```bash
git clone https://github.com/Eirik2020/TTK4225_plant_watering_system.git
cd TTK4225_plant_watering_system
```

Connect the flashed ESP32 to a USB-A port on the Pi using a data-capable USB
cable. Confirm that Linux sees its CP2102 USB-to-UART bridge:

```bash
lsusb
ls -l /dev/serial/by-id/
```

The service uses `/dev/serial/by-id/...` instead of `/dev/ttyUSB0` because the
by-ID name remains stable when device numbers change.

## 2. Install and start the service

Run the tracked installer from the repository root. The `--name` value becomes
the CSV filename prefix and the systemd instance name:

```bash
sudo bash deploy/raspberry-pi/install-service.sh --name soil_measurement
```

The installer:

1. Detects the stable serial-device path.
2. Creates `.venv` when necessary and installs `python/requirements.txt`.
3. Adds the service account to `dialout`.
4. Creates `python/data/` with suitable ownership.
5. Renders and installs `plant-measurement@.service` and its environment file.
6. Enables and starts the requested measurement instance.

If multiple serial devices are connected, choose one explicitly:

```bash
sudo bash deploy/raspberry-pi/install-service.sh \
  --name soil_measurement \
  --serial-port /dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0
```

Use `--no-start` to install everything without starting a measurement. Use
`--user USER` or `--repo-dir PATH` only when automatic detection is not
appropriate. Run the installer with `--help` for all options.

### Migrating the original non-template service

Early versions of this Pi setup installed `plant-measurement.service` directly.
Stop and disable that unit before running the tracked installer so only one
process can own the serial port:

```bash
sudo systemctl disable --now plant-measurement.service
sudo bash deploy/raspberry-pi/install-service.sh --name soil_measurement
```

## 3. Start a named measurement

Only one measurement instance should run at a time because a serial port can
have only one reader. Stop the previous instance, then start and enable the new
one:

```bash
sudo systemctl disable --now plant-measurement@soil_measurement.service
sudo systemctl enable --now plant-measurement@tomato_test.service
```

Use a short name containing letters, digits, dots, underscores, or hyphens.
Starting `plant-measurement@tomato_test.service` creates a file resembling:

```text
python/data/tomato_test_20260825_153000.csv
```

The suffix is the Pi's local time when the logger process starts. Restarting a
service creates a new file with a new timestamp rather than overwriting an old
measurement.

## 4. Inspect or stop the service

Check whether a named instance is running and enabled at boot:

```bash
systemctl status plant-measurement@tomato_test.service
systemctl is-active plant-measurement@tomato_test.service
systemctl is-enabled plant-measurement@tomato_test.service
```

Follow new readings in the system journal:

```bash
journalctl -u plant-measurement@tomato_test.service -f
```

Stop it for the current boot while leaving it enabled for the next boot:

```bash
sudo systemctl stop plant-measurement@tomato_test.service
```

Stop it and prevent automatic startup:

```bash
sudo systemctl disable --now plant-measurement@tomato_test.service
```

Restarting is useful after reconnecting the ESP32, although the service already
retries automatically after serial errors:

```bash
sudo systemctl restart plant-measurement@tomato_test.service
```

List all currently loaded measurement instances:

```bash
systemctl list-units 'plant-measurement@*.service'
```

## 5. Inspect timestamps and CSV data

List files with their sizes and modification timestamps:

```bash
ls -lht --time-style=long-iso ~/TTK4225_plant_watering_system/python/data/
```

Read the latest rows from one file:

```bash
tail -n 10 ~/TTK4225_plant_watering_system/python/data/tomato_test_20260825_153000.csv
```

Each row contains the Pi's local timestamp and the ESP32's filtered raw ADC
value:

```csv
timestamp,adc_filtered_raw
2026-08-25T15:30:10.412+02:00,2884
2026-08-25T15:30:20.412+02:00,2885
```

Verify the Pi's timezone and network-clock synchronization before a long run:

```bash
timedatectl status
```

## 6. Connect and download data from Windows

Connect from PowerShell:

```powershell
ssh ferropi@ferropi.local
```

After inspecting or stopping the measurement, leave SSH with `exit`. Download
one file into the current Windows directory:

```powershell
scp "ferropi@ferropi.local:/home/ferropi/TTK4225_plant_watering_system/python/data/tomato_test_20260825_153000.csv" .
```

Download every CSV into a local `measurements` directory:

```powershell
New-Item -ItemType Directory -Force measurements
scp "ferropi@ferropi.local:/home/ferropi/TTK4225_plant_watering_system/python/data/*.csv" ".\measurements\"
```

Copying a file while logging is active produces a snapshot through the most
recently flushed row. Stop the service first when downloading the final version
of an experiment.

## 7. Update an existing installation

Stop the active instance, update the checkout, and rerun the installer:

```bash
sudo systemctl stop plant-measurement@soil_measurement.service
git pull --ff-only
sudo bash deploy/raspberry-pi/install-service.sh --name soil_measurement
```

Rerunning the installer updates the Python dependencies, rendered service, and
environment file, then restarts the selected instance.

## Troubleshooting

If Python reports that no serial ports are detected, check Linux first:

```bash
lsusb
ls -l /dev/serial/by-id/ /dev/ttyUSB* 2>/dev/null
journalctl -k -n 50 --no-pager
```

The ESP32-DEV-38P normally appears as a Silicon Labs CP2102 device. If it does
not appear in `lsusb`, check the USB cable and Pi USB-A port before changing
Python or service configuration. A power-only or faulty cable can power the
board without providing a working data connection.
