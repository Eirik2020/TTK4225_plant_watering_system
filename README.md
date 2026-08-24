# TTK4225 plant watering system

Bare-metal Rust firmware for the **Seeit ESP32-DEV-38P** development board,
using [Embassy](https://embassy.dev/) and
[esp-hal](https://docs.espressif.com/projects/rust/esp-hal/latest/).

The board uses the classic ESP32-WROOM-32 module. This is an Xtensa ESP32—not
an ESP32-C6—so the repository targets `xtensa-esp32-none-elf` with Espressif's
Rust toolchain.

Board reference: [Seeit ESP32-DEV-30P/38P datasheet](https://docs.rs-online.com/7729/A700000011181234.pdf).

The initial firmware prints a hello-world message over UART and asynchronously
toggles GPIO2 every 500 ms.

The repository is a Cargo workspace: embedded source lives under `firmware/`,
while the project report lives under `latex/`. Cargo commands can still be run
from the repository root because `firmware` is the default workspace member.

## LED

GPIO2 is commonly connected to the controllable status LED on 38-pin ESP32
development boards. If the LED on your particular board is only a power LED,
connect an external LED instead:

```text
GPIO2 ---- 220-1000 ohm resistor ---- LED anode (+)
GND   ------------------------------ LED cathode (-)
```

GPIO2 is a boot-strapping pin. The circuit above is safe for this example, but
avoid external circuitry that forces it high during reset.

## Prerequisites

Install [Rust](https://rustup.rs/), Espressif's Xtensa Rust toolchain, and the
flashing utility:

```powershell
cargo install espup --locked
espup install
cargo install espflash --locked
```

On Windows, `espup` configures the toolchain environment automatically. Restart
the terminal after installation if the `esp` toolchain is not found. The board's
USB-to-UART bridge may also require a CP210x or CH340 driver, depending on the
board revision.

## Build

```powershell
cargo build --release
```

## Flash and monitor

Connect the board over USB, then run:

```powershell
cargo run --release
```

The runner in `.cargo/config.toml` builds, flashes with `espflash`, and opens the
serial monitor. Press `Ctrl+C` to exit. If automatic reset does not enter the
bootloader, hold **BOOT**, press and release **EN/RESET**, then release **BOOT**
and retry.

Expected monitor output:

```text
Hello, world from Embassy on the ESP32-DEV-38P!
LED on
LED off
...
```

## Useful commands

```powershell
cargo +stable fmt --check
cargo check
cargo build --release
cargo clean
```

The project follows the current
[`esp-generate`](https://github.com/esp-rs/esp-generate) Embassy layout and pins
the ESP HAL 1.1 release line. Embassy's runtime currently requires the HAL's
`unstable` feature, so minor HAL updates can require small API adjustments.

## Report

The project report lives in [`latex/`](latex/). Build it on Windows with:

```powershell
cd latex
.\scripts\build.ps1
```

The finished document is written to `latex/dist/report.pdf`. See
[`latex/README.md`](latex/README.md) for the native, Docker, VS Code, and clean
build options.
