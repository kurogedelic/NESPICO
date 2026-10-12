# PIO bring-up checkpoint

Date: 2026-10-12

## Repository state verified before this work

- The public repository is not empty: `main` contains the host simulator, 21
  regression tests, CI, architecture notes, and a staged PCB go/no-go roadmap.
- `main` is the only remote branch currently present. Its latest host-simulation
  GitHub Actions run was successful.
- The next documented milestone is a real PIO sequencer on the existing RP2350A
  Zero; the roadmap explicitly blocks PCB fabrication until timing and electrical
  checks pass.

## Added in this checkpoint

`firmware/pio_bringup/` contains a Pico SDK 2.3.1 CMake target and a two-state-
machine PIO loopback test. GPIO assignments are test-only defaults and may be
changed at configure time. Two isolated 3.3 V jumpers let the firmware compare
concurrent 32-bit streams, report 99 nominal PIO instruction clocks per word,
and expose sticky TX/RX stall flags. The test is deliberately not connected to a
cartridge bus.

The local firmware build completed without compiler warnings. `picotool info`
recognized the generated UF2 as an ARM Secure RP2350 image with USB stdin/stdout;
the image is only a compile artifact and has not been flashed or run on hardware.

The new `RP2350 firmware build` workflow compiles the firmware and produces a
UF2 artifact when run in GitHub Actions. A successful compile proves only that
the source assembles and links for the Pico 2 / RP2350A SDK target.

## Verification still required

1. Confirm the new GitHub Actions firmware job passes on the feature branch.
2. Confirm the exact YD-RP2350A Zero board identity and the exposed pin numbers.
3. Flash the isolated loopback test, verify both jumpers and synchronized strobes
   with a logic analyzer while USB is active, and keep the cartridge disconnected.
4. Implement and measure the actual latch/transceiver bus sequencer and bound
   address-producer / DMA deadlines.
5. Complete the 60-pin signal matrix, 5 V protection review, pin allocation,
   reviewed schematic and priced two-unit BOM before deciding whether to release
   PCB files for fabrication.

No real hardware is attached to this computer, so steps 2–4 cannot be reported as
measured here. No PCB has been ordered or represented as electrically validated.

## Software-only verification and board-documentation check — 2026-10-12

- Re-ran all **28/28** host regression tests successfully.
- Performed a clean Pico SDK 2.3.1 configure/build for the default test GPIO map
  and a second, non-overlapping test map (GPIO 9–14); both produced a UF2.
- Confirmed that CMake rejects both a duplicate GPIO assignment and GPIO 30
  before compilation. Equivalent negative cases are now in the firmware workflow;
  the feature-branch GitHub Actions result is still unverified.
- Added a configure-time range check (0–29) and uniqueness check for the six
  loopback signals. These checks validate only the numeric silicon GPIO domain,
  not which pads a carrier module exposes or whether any electrical connection
  is safe.
- Public product documentation did **not** establish that the recorded
  `YD-RP2350A Zero` is the same hardware as Waveshare's `RP2350-Zero`. The
  [Waveshare wiki](https://www.waveshare.com/wiki/RP2350-Zero) describes an
  RP2350A module with 29 GPIOs (20 on headers, the rest solder-only), but its
  feature text says 4 MB flash while the linked
  [official schematic](https://files.waveshare.com/wiki/RP2350-Zero/RP2350_Zero.pdf)
  shows a W25Q16 device (16 Mbit / 2 MB). A separate
  [RP2350-Zero-CM guide](https://spotpear.com/wiki/Raspberry-Pi-Pico-2-RP2350-Zero-CM-Mini.html)
  documents another product variant. Do not infer the target board's pin exposure,
  flash size, layout, or onboard GPIO sharing from these similar names.
- No board-specific GPIO map was frozen; no firmware was flashed and no physical
  signal or electrical behavior was measured.

## Target-board clarification and follow-up — 2026-10-12

- The target is now specified as the standard, non-wireless **Raspberry Pi Pico 2**, replacing the earlier YD-RP2350A Zero assumption. Raspberry Pi's official documentation lists 26 header GPIOs: GP0–GP22 and GP26–GP28; GP23/24/25/29 serve on-board functions. The PIO CMake guard and CI's alternate map now enforce this header set. GP26–GP28 are ADC-capable and remain valid digital pins for the isolated 3.3 V loopback, but do not overdrive them or drive them while the board is unpowered; GP29 is the VSYS monitor and is not exposed as a header GPIO.
- The earlier 27-GPIO concept is one pin larger than Pico 2's exposed GPIO set. Stage 2 must reduce the MCU pin count or deliberately use reviewed external logic; no pin map is frozen by this clarification.
- Commit `8f26041` was pushed to `work/rp2350-pio-bringup`; both the host-simulation and `pio-bringup` GitHub Actions workflows passed for that commit. No physical Pico 2 was confirmed on the bench, no firmware was flashed, and no electrical waveform was measured.
- Official sources: [Pico 2 datasheet](https://pip.raspberrypi.com/documents/RP-008299-DS) and [Raspberry Pi Pico-series board documentation](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html).
