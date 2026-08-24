fn main() {
    // Keep the ESP HAL linker script last.
    println!("cargo:rustc-link-arg=-Tlinkall.x");
}
