#![no_std]
#![no_main]

use embassy_executor::Spawner;
use embassy_time::{Duration, Ticker};
use esp_backtrace as _;
use esp_hal::{
    analog::adc::{Adc, AdcConfig, Attenuation},
    clock::CpuClock,
    gpio::{Level, Output, OutputConfig},
    interrupt::software::SoftwareInterruptControl,
    timer::timg::TimerGroup,
};

use esp_println::println;

const ADC_SAMPLE_INTERVAL_MS: u64 = 10;
const ADC_SAMPLES_PER_REPORT: u32 = 1_000;
const HEARTBEAT_TOGGLE_INTERVAL_MS: u64 = 1_000;

// Creates the application descriptor expected by the ESP-IDF bootloader.
esp_bootloader_esp_idf::esp_app_desc!();

#[embassy_executor::task]
async fn heartbeat(mut led: Output<'static>) {
    let mut ticker = Ticker::every(Duration::from_millis(HEARTBEAT_TOGGLE_INTERVAL_MS));

    loop {
        led.toggle();
        ticker.next().await;
    }
}

#[esp_rtos::main]
async fn main(spawner: Spawner) -> ! {
    let config = esp_hal::Config::default().with_cpu_clock(CpuClock::max());
    let peripherals = esp_hal::init(config);

    // Start Embassy's time driver and executor support.
    let timer_group = TimerGroup::new(peripherals.TIMG0);
    let software_interrupt = SoftwareInterruptControl::new(peripherals.SW_INTERRUPT);
    esp_rtos::start(timer_group.timer0, software_interrupt.software_interrupt0);

    // Toggling once per second produces a complete on/off heartbeat at 0.5 Hz.
    let led = Output::new(peripherals.GPIO2, Level::Low, OutputConfig::default());
    spawner.spawn(heartbeat(led).unwrap());

    let mut adc_config = AdcConfig::new();
    let mut analog_pin = adc_config.enable_pin(peripherals.GPIO34, Attenuation::_11dB);
    let mut adc = Adc::new(peripherals.ADC1, adc_config);

    println!("Hello, world from Embassy on the ESP32-DEV-38P!");
    println!("Sampling ADC1 GPIO34 at 100 Hz; reporting a 1000-sample average at 0.1 Hz.");

    let mut sample_ticker = Ticker::every(Duration::from_millis(ADC_SAMPLE_INTERVAL_MS));
    let mut sample_sum = 0_u32;
    let mut sample_count = 0_u32;

    loop {
        let raw: u16 = nb::block!(adc.read_oneshot(&mut analog_pin)).unwrap();
        sample_sum += u32::from(raw);
        sample_count += 1;

        if sample_count == ADC_SAMPLES_PER_REPORT {
            let filtered_raw = sample_sum / ADC_SAMPLES_PER_REPORT;
            println!("MOISTURE filtered_raw={filtered_raw} samples={ADC_SAMPLES_PER_REPORT}");

            sample_sum = 0;
            sample_count = 0;
        }

        sample_ticker.next().await;
    }
}
