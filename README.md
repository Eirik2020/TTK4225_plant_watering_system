# TTK4225 plant watering system

An ESP32-based automatic plant watering system developed as part of TTK4225 at
the Norwegian University of Science and Technology (NTNU).

This repository is a Rust and Embassy implementation inspired by the ITK
student-active learning project
[Plants-watering-system](https://github.com/Microlabs-Project-ITK-NTNU/Plants-watering-system).
The project is organized around three core goals:

1. Measure soil moisture.
2. Control a water pump safely.
3. Use the measured moisture level to decide when the plant should be watered.

## Current status

| Area | Status |
| --- | --- |
| ESP32 firmware workspace | Implemented |
| Asynchronous Embassy runtime | Implemented |
| GPIO2 heartbeat LED | Implemented at 0.5 Hz |
| ADC sampling on GPIO34 | 100 Hz sampling; 0.1 Hz filtered raw output |
| Soil-sensor calibration | In progress |
| Pump driver and pump control | Planned |
| Automatic watering logic | Planned |
| LaTeX project report | Set up; CI workflow configured |
| Python USB serial reader and CSV logger | Implemented |
| Raspberry Pi unattended logger service | Implemented; reproducible installer included |
| Python plotting or data processing | Planned |

The firmware samples the ADC at 100 Hz and calculates one non-overlapping
1,000-sample average every 10 seconds. That filtered raw value is sent over
serial at 0.1 Hz. The status LED completes one on/off heartbeat cycle every two
seconds. The firmware does not yet operate a pump or make automatic watering
decisions.

## Hardware

The firmware targets the **Seeit ESP32-DEV-38P**, which uses the classic
ESP32-WROOM-32 module. This is an Xtensa ESP32, not an ESP32-C6, so the Rust
target is `xtensa-esp32-none-elf`.

Board reference:
[Seeit ESP32-DEV-30P/38P datasheet](https://docs.rs-online.com/7729/A700000011181234.pdf).

### Current pin assignment

| Function | ESP32 pin | Notes |
| --- | --- | --- |
| Status LED | GPIO2 | Common on-board LED connection |
| Soil-moisture analog input | GPIO34 | ADC1 input; input-only GPIO |
| Pump control | TBD | Requires an external driver circuit |

For an analog moisture sensor, connect its analog output to GPIO34 and its
ground to ESP32 ground. Ensure the sensor output never exceeds the ESP32 GPIO
voltage limit.

Do not power a pump directly from an ESP32 GPIO. Use a suitable MOSFET,
transistor, or relay driver, an appropriate pump power supply, a common ground,
and inductive-load protection where required.

## Repository layout

```text
.
|-- .cargo/                 ESP32 target and espflash runner configuration
|-- .github/workflows/      Automated LaTeX report build
|-- deploy/raspberry-pi/    Reproducible Raspberry Pi service installation
|-- docs/                   Deployment and operating guides
|-- firmware/               Bare-metal Rust firmware crate
|   |-- src/bin/main.rs     Firmware entry point
|   |-- Cargo.toml          Firmware dependencies
|   `-- build.rs            ESP32 linker configuration
|-- latex/                  Project report and build scripts
|-- python/                 USB serial reader, CSV logger, and calibration tools
|-- Cargo.toml              Cargo workspace configuration
|-- Cargo.lock              Locked Rust dependencies
`-- rust-toolchain.toml     Espressif Rust toolchain selection
```

The `firmware` crate is the default Cargo workspace member, so all Cargo
commands below can be run from the repository root.

Clone the repository with:

```powershell
git clone https://github.com/Eirik2020/TTK4225_plant_watering_system.git
cd TTK4225_plant_watering_system
```

## Firmware setup

### Prerequisites

Install [Rust](https://rustup.rs/), Espressif's Xtensa Rust toolchain, and
`espflash`:

```powershell
cargo install espup --locked
espup install
cargo install espflash --locked
```

Restart the terminal after installing the toolchain. On Windows, the board's
USB-to-UART bridge may also require a CP210x or CH340 driver, depending on the
board revision.

### Build

```powershell
cargo build --release
```

### Flash and monitor

Connect the board over USB and run:

```powershell
cargo run --release
```

The runner in `.cargo/config.toml` flashes the classic ESP32 and opens the
serial monitor. Press `Ctrl+C` to exit.

If automatic reset does not enter the bootloader, hold **BOOT**, press and
release **EN/RESET**, release **BOOT**, and retry the command. You can inspect
all detected serial ports with:

```powershell
espflash board-info --list-all-ports
```

Expected monitor output resembles:

```text
Hello, world from Embassy on the ESP32-DEV-38P!
Sampling ADC1 GPIO34 at 100 Hz; reporting a 1000-sample average at 0.1 Hz.
MOISTURE filtered_raw=2087 samples=1000
MOISTURE filtered_raw=2091 samples=1000
...
```

The reported number remains in raw ADC units; no moisture-percentage or voltage
conversion is applied. Its exact value depends on the connected sensor and
moisture condition.

## Read and log ADC samples with Python

The Python reader listens to the firmware output over USB serial, extracts the
`MOISTURE filtered_raw` messages, prints them to the terminal, and appends them
to a CSV file using the computer's local clock.

Install its dependency from the repository root:

```powershell
python -m pip install -r python/requirements.txt
```

Flash the firmware first, then close the `espflash` serial monitor with
`Ctrl+C`. Only one program can use COM8 at a time. Start the reader and provide
a name for the measurement session with:

```powershell
python python/main.py soil_dry
```

This creates a new file such as
`python/data/soil_dry_20260824_130541.csv`. The timestamp suffix comes from the
computer's local clock when the script starts. If the name is omitted, it
defaults to `adc_readings`.

COM8, 115200 baud, and the `python/data` output directory are the defaults.
Override them when necessary:

```powershell
python python/main.py soil_wet --port COM9 --baudrate 115200
python python/main.py soil_wet --output-dir measurements
```

List detected serial ports or display every firmware message with:

```powershell
python python/main.py --list-ports
python python/main.py --all
```

Expected output:

```text
Listening for ADC readings on COM8 at 115200 baud.
Logging samples to C:\...\python\data\soil_dry_20260824_130541.csv.
Press Ctrl+C to stop.
2026-08-24T13:05:41.321+02:00 | Filtered ADC raw value: 2087
2026-08-24T13:05:51.321+02:00 | Filtered ADC raw value: 2091
...
```

The CSV file is append-only and has the following format:

```csv
timestamp,adc_filtered_raw
2026-08-24T13:05:41.321+02:00,2087
2026-08-24T13:05:51.321+02:00,2091
```

### Useful firmware commands

```powershell
cargo +stable fmt --all -- --check
cargo check
cargo build --release
cargo clean
```

The firmware uses [Embassy](https://embassy.dev/) with
[esp-hal](https://docs.espressif.com/projects/rust/esp-hal/latest/) 1.1. The
Embassy runtime currently requires the HAL's `unstable` feature, so minor HAL
updates can require API changes.

## Raspberry Pi unattended logging

The repository includes a systemd template service and installer for recording
measurements continuously on a Raspberry Pi. From a clone on the Pi, connect
the ESP32 over USB and run:

```bash
sudo bash deploy/raspberry-pi/install-service.sh --name soil_measurement
```

The installer detects the stable `/dev/serial/by-id/...` device, prepares the
Python virtual environment and serial permissions, and enables a named service
instance at boot. The instance name becomes the CSV filename prefix; the logger
adds its start timestamp automatically.

See [`docs/raspberry-pi.md`](docs/raspberry-pi.md) for the complete fresh-Pi
setup, migration from the original service, custom measurement names, service
control, timestamp inspection, troubleshooting, and Windows `scp` download
commands.

## Soil-moisture calibration

Raw ESP32 ADC readings are not absolute moisture percentages. A practical
two-point calibration procedure is:

1. Record several readings with the probe in the chosen dry reference
   condition.
2. Record several readings at the soil's field-capacity reference condition.
3. Average or filter the readings to reduce noise.
4. Map values between the dry and wet references to a relative moisture scale.
5. Validate the chosen watering threshold using the actual plant and soil.

Calculate the current reference calibration with:

```powershell
python python/calibrate.py soil_dry_ref1 soil_field_cap_ref1
```

The names are resolved to the newest matching timestamped CSV files under
`python/data`. By default, the script uses the median of the final 100 filtered
reports from each file to reduce the influence of startup drift and outliers.
For the current datasets this produces:

```text
Dry reference:           ADC 2852
Field-capacity reference: ADC 2194
ADC span:                    658
```

The resulting scale maps the dry reference to 0% and field capacity to 100%.
It is a relative calibration, not absolute volumetric water content. Save the
complete statistics and coefficients as JSON with:

```powershell
python python/calibrate.py soil_dry_ref1 soil_field_cap_ref1 `
    --output python/calibration_ref1.json
```

The selected endpoint window and estimator can also be changed:

```powershell
python python/calibrate.py soil_dry_ref1 soil_field_cap_ref1 `
    --tail-samples 200 --estimator mean
```

Calibration results and methodology belong in
[`latex/chapters/soil_cal.tex`](latex/chapters/soil_cal.tex).

## Report

The project report lives under [`latex/`](latex/). Build it on Windows with:

```powershell
cd latex
.\scripts\build.ps1
```

The script uses a native `latexmk` installation when available and otherwise
falls back to Docker. The finished document is written to
`latex/dist/report.pdf`.

With the recommended VS Code LaTeX Workshop extension:

- `Ctrl+Alt+B` builds the report;
- `Ctrl+Alt+V` opens the PDF preview;
- saving a LaTeX file rebuilds and refreshes the split-screen preview.

See [`latex/README.md`](latex/README.md) for native, Docker, clean-build, and
editor details. GitHub Actions also builds the report and uploads the PDF as a
workflow artifact.

## Planned work

- Validate the soil-moisture calibration against additional reference runs.
- Validate multi-week moisture logging and recovery after power or USB faults.
- Select and validate a safe pump driver and power architecture.
- Add watering thresholds, hysteresis, maximum run time, and fault handling.
- Plot moisture measurements over time using the `python/` tools.
- Consider a reservoir-level sensor and local or web-based status reporting.

## Acknowledgements

The project direction and learning milestones are based on the open-source
[Microlabs Project at NTNU's Department of Engineering Cybernetics](https://github.com/Microlabs-Project-ITK-NTNU/Plants-watering-system).
