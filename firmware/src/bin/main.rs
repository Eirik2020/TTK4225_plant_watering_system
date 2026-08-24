#![no_std]
#![no_main]

use embassy_executor::Spawner;
use embassy_time::{Duration, Timer};
use esp_backtrace as _;
use esp_hal::{
    analog::adc::{Adc, AdcConfig, Attenuation},
    clock::CpuClock,
    gpio::{Level, Output, OutputConfig},
    interrupt::software::SoftwareInterruptControl,
    timer::timg::TimerGroup,
};

use esp_println::println;

// Creates the application descriptor expected by the ESP-IDF bootloader.
esp_bootloader_esp_idf::esp_app_desc!();

#[esp_rtos::main]
async fn main(_spawner: Spawner) -> ! {
    let config = esp_hal::Config::default().with_cpu_clock(CpuClock::max());
    let peripherals = esp_hal::init(config);

    // Start Embassy's time driver and executor support.
    let timer_group = TimerGroup::new(peripherals.TIMG0);
    let software_interrupt = SoftwareInterruptControl::new(peripherals.SW_INTERRUPT);
    esp_rtos::start(timer_group.timer0, software_interrupt.software_interrupt0);

    // The ESP32-DEV-38P status LED is commonly connected to GPIO2.
    let mut led = Output::new(peripherals.GPIO2, Level::Low, OutputConfig::default());

    let mut adc_config = AdcConfig::new();
    let mut analog_pin = adc_config.enable_pin(peripherals.GPIO34, Attenuation::_11dB);
    let mut adc = Adc::new(peripherals.ADC1, adc_config);

    println!("Hello, world from Embassy on the ESP32-DEV-38P!");

    loop {
        led.toggle();

        let raw: u16 = nb::block!(adc.read_oneshot(&mut analog_pin)).unwrap();

        println!("ADC raw value: {raw}");

        Timer::after(Duration::from_millis(500)).await;
    }
}
