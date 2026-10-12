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
