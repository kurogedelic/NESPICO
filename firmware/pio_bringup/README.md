# RP2350 dual-lane PIO loopback bring-up

This is a **test fixture firmware**, not a cartridge interface and not evidence
that live NES bus timing is feasible. It proves the SDK/PIO build path, runs two
state machines in sync, checks bit ordering through jumper loopbacks, and reports
PIO instruction-count and FIFO-stall status while USB CDC may be active.

## Safety boundary

- Keep the Famicom cartridge and every 5 V signal disconnected.
- Use only the RP2350 board's 3.3 V GPIO pins.
- With the default pin map, add short jumper wires `GPIO2 -> GPIO3` and
  `GPIO6 -> GPIO7`; the strobe outputs are GPIO4 and GPIO8.
- Check the exact module pinout first. Override the six GPIO values at CMake
  configure time if those pins are unavailable or conflict with board circuitry.
- The fixture targets the standard, non-wireless Raspberry Pi Pico 2. CMake
  accepts only header GPIOs GP0..GP22 and GP26..GP28, and rejects duplicate
  assignments among the six test signals. GP23/24/25/29 are reserved for
  on-board functions. GP26..GP28 are ADC-capable but can be used as digital GPIO;
  their input protection diode means input must not exceed IOVDD by more than
  about 300 mV, and they must not be driven while the Pico 2 is unpowered. This check cannot
  establish electrical safety or cartridge compatibility; no GPIO may connect
  directly to a 5 V cartridge signal.
- The loopback input pins have internal pull-downs. The outputs start low.

## Build

Use Raspberry Pi's Pico SDK **2.3.1** and its documented ARM toolchain packages.
The host-side build can be run with:

```sh
cmake -S firmware/pio_bringup -B build/pio-bringup \
  -G Ninja -DPICO_BOARD=pico2 -DPICO_SDK_PATH=/path/to/pico-sdk
cmake --build build/pio-bringup
```

The output includes `nespico_pio_bringup.uf2`. `pico2` selects the official
Raspberry Pi Pico 2 board target for compile validation. The firmware can also
be configured with different header GPIOs, e.g.
`-DNESPICO_PIN_A_OUT=...` and corresponding input/strobe/lane-B definitions.
Invalid values can be checked without hardware: configure once with a duplicate
such as `-DNESPICO_PIN_A_IN=2`, an out-of-range value such as
`-DNESPICO_PIN_A_OUT=30`, and an on-board-reserved pin such as
`-DNESPICO_PIN_A_OUT=24`; all configurations must fail before compilation.
The alternate GP20..GP22/GP26..GP28 map in CI is compile-only; it has not been
physically looped back. The default wiring instructions below use GP2..GP8.
The source-level PIO instruction and cycle-count consistency check is also
hardware-independent:

```sh
python3 firmware/pio_bringup/validate_pio_source.py
```

## Test behavior

- PIO0 state machines 0 and 1 are enabled in sync and run separate 32-bit test
  streams for 4,096 words per lane per round.
- Each data bit is driven on a lane's output, sampled one PIO clock later on its
  loopback input, and accompanied by a one-cycle strobe.
- Nominal PIO path: 1 `pull` + 1 `set` + 32 × (`out` + `in` + `jmp`) + 1 `push`
  = **99 instruction clocks per 32-bit word**, excluding FIFO stalls and GPIO
  propagation. This is a test-pattern count, not a cartridge transaction time.
- `validate_pio_source.py` checks the source instruction order, sample strobe
  side-set, loop width, and matching C constants. It is a consistency check, not
  a PIO emulator or a substitute for loopback measurements.
- A pass requires exact data matches and no sticky TXSTALL/RXSTALL flags. The
  report includes elapsed MCU time, `clk_sys`, USB connection state and mismatch
  count. USB progress messages are emitted only when the USB CDC host is present.
- A logic analyzer on GPIO4/GPIO8 can verify sample strobes; probe the loopback
  outputs only after verifying the board's 3.3 V pinout and electrical limits.

## What this does not validate

This one-bit-per-lane harness does not validate the 60-pin connector, 5 V level
translation, latch/transceiver timing, actual CPU/PPU address production, DMA,
cartridge IRQ/CIRAM behavior, USB application throughput, or a playable game.
Those still block freezing a schematic or ordering PCBs. The next firmware step
is an 8-bit latch/transceiver test with a board-specific pin map and captured
logic-analyzer traces.
