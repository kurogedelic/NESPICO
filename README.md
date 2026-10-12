# NESPICO

A low-cost USB Famicom cartridge reader and **live-cartridge console** experiment.

The cartridge is not just a source for a ROM dump: the eventual console should drive the inserted physical cartridge's CPU and PPU buses while running the NES CPU/PPU/APU on an RP2350. The host PC or Mac handles display, audio playback, and controls.

## Project overview

```text
Physical Famicom 60-pin cartridge
               |
     74-series bus interface
     (latches / transceivers)
               |
      YD-RP2350A Zero + PIO
               |
           USB Full Speed
               |
           PC / Mac host
   video, audio, controls, dumps
```

**Target hardware:** inexpensive YD-RP2350A Zero (RP2350A), 74-series logic, a real 60-pin cartridge connector and USB. No FPGA, HDMI shield or wireless module. GPIO allocation and electrical protection are not yet finalized.

## Goals

1. **Play real cartridges.** Read PRG and CHR from the inserted cartridge during execution, support cartridge-side bank switching, CHR-RAM and mapper-generated IRQs instead of silently substituting a fully dumped ROM.
2. **Dump cartridges.** Read PRG-ROM and CHR-ROM to a host computer over USB, verify dumps, and support applicable mapper-controlled banks and cartridge save RAM.
3. **Reproduce physical-console behavior.** Keep motherboard RAM across RESET and cartridge replacement with power retained. Test tricks such as **Tennis → Super Mario Bros. World 9**. This is **not** a request for automatic hot-swap detection or live game switching; cartridge removal with power applied also needs electrical safety validation.
4. **Use the computer as the display.** Stream enough video/audio information over USB for a small PC/Mac viewer, and receive controller input from the host. USB Full Speed means raw full-frame 60fps video is not a feasible default protocol.
5. **Keep the hardware inexpensive and buildable in a quantity of two.** Prefer off-the-shelf RP2350A Zero boards, inexpensive standard logic and hand-assembled connectors to a custom MCU/FPGA board.

## Development approach

**Simulation first, hardware second.** The host-side simulator models approximate NTSC CPU/PPU bus demand, nominal 74-series/PIO transaction latency, overlapping requests, simplified MMC3 A12 qualification, RESET RAM retention and USB bandwidth assumptions. GitHub Actions runs the tests without any connected hardware.

The simulation is a *screening tool*, not proof that physical timing works. It does not execute actual PIO, emulate a complete 6502/PPU, validate the cartridge voltage interface, or establish real USB throughput.

### Current status

- Host-side deterministic bus-timing simulator and 21 regression tests are committed. All 21 passed in a local Python run; GitHub Actions execution has not been verified.
- GPIO pin map, 5V interface, physical timing, accurate NES emulator, cartridge swapping and USB video protocol remain to be validated.
- **No claim of working cartridge playback or real-device ROM dumping yet.**

### Local checks

```sh
python -m unittest discover -s tests -v
python -m nespico.cli --scanlines 262
python -m nespico.cli --sys-mhz 20 --settle-ns 160 --scanlines 1 # expected failure
```

## Development records

- [Development log (2026-10-12)](docs/journal/2026-10-12.md)
- [Development roadmap](docs/roadmap.md)
- [Simulation results](docs/benchmark-results.md)

## Milestones

1. CI timing simulator + executable design assumptions
2. PIO bus-pattern generator on RP2350A Zero, measured with loopback and a logic analyzer
3. 74-series interface prototype: safe NROM PRG/CHR readback
4. USB dumper with validation and mapper-aware read/write
5. Real-cart CPU+PPU operation, host video/audio and input
6. RAM-preserving RESET, cartridge replacement tests and MMC1/MMC3

See [architecture notes](docs/architecture.md) and [simulation results](docs/benchmark-results.md). The extra pipeline tests model the CPU/PPU work required to prepare addresses; they show that nominal bus-only timing success is not sufficient.

Reference documentation: [NESdev cartridge connector](https://www.nesdev.org/wiki/Cartridge_connector), [PPU rendering](https://www.nesdev.org/wiki/PPU_rendering), [MMC3](https://www.nesdev.org/wiki/MMC3), [RP2350](https://www.raspberrypi.com/documentation/microcontrollers/silicon.html).
