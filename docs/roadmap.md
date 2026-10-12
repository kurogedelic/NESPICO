# Roadmap

The objective is a **two-unit prototype** of a USB-connected Famicom cartridge dumper and real-cartridge NES console. Start with YD-RP2350A Zero + 74-series logic, no FPGA, no HDMI or Wi-Fi. The computer displays video/audio and forwards controls, while the RP2350 executes the emulator and talks to actual cartridge PRG/CHR buses.

## Stage 0 — Host-side verification (in progress)

- [x] Implement an approximate NTSC CPU/PPU bus timing scheduler.
- [x] Compare independent vs shared-bus latencies.
- [x] Model CPU/PPU work required to prepare bus requests.
- [x] Add basic RESET RAM retention and partial MMC3 A12 tests.
- [x] Commit 21 Python regression tests and a GitHub Actions workflow.
- [x] Verify green GitHub Actions results on the main branch.
- [ ] Replace synthetic bus events with vetted 6502 instruction and PPU fetch traces.
- [ ] Model actual M2 phases, latch writes, /OE, IRQ, CIRAM, read/write turnarounds and bus contention.
  - [x] Add a host-only abstract data-bus owner guard with a tested disabled step on driver handoff; this does not model real strobes, timing, or electrical behavior.

**Pass condition:** reproducible CI and timing simulations with assumptions explicitly labeled. Host simulation cannot prove hardware performance.

## Stage 1 — Real PIO proof on the existing RP2350A Zero

- [x] Add a Pico SDK 2.3.1 build target and a first real PIO assembly loopback sequencer.
- [x] Define a test-only dual-lane GPIO map and command/data format; do not treat it as the cartridge pin map.
- [x] Add synchronized CPU/PPU-like state-machine streams and report instruction-cycle and FIFO stall status.
- [x] Add a GitHub Actions firmware build workflow.
- [x] Build locally against Pico SDK 2.3.1 and verify the UF2 identifies as RP2350.
- [ ] Confirm the new GitHub Actions firmware build on the feature branch.
- [ ] Confirm exact board model and physically exposed test GPIOs.
- [ ] Verify sample strobes and loopback waveforms on the board with USB active.
- [ ] Add a real 8-bit latch/transceiver transaction path and measure FIFO/DMA starvation.
- [ ] Measure worst-case producer timing for simultaneous CPU/PPU requests.

**Pass condition:** observed bus operations meet timing deadlines under representative sustained load, with no missed requests or FIFO starvation. Report clocks, stalls and limitations.

## Stage 2 — Complete electrical interface before PCB

- [ ] Enumerate each 60-pin cartridge signal, direction, voltage, required timing and ownership.
- [ ] Finalize the **27 GPIO plus 74-series** map; check physically available pins on the Zero.
- [ ] Choose precise latch/buffer/voltage-interface part numbers, validating 3.3 V output recognition at 5 V loads.
- [ ] Verify bus isolation and safe default levels during reset, boot, and cartridge removal.
- [ ] Define CIRAM implementation (including whether separate SRAM is required), mapper IRQ and expansion-audio scope.
- [ ] Produce reviewed schematics and a priced BOM for **two boards**.

**Pass condition:** all necessary signals are driven or sensed correctly, with no drive-direction conflicts and no unresolved protection problems. Only then order the PCB.

## Stage 3 — Cartridge dumper

- [ ] Assemble interface and verify power rails and default bus states without cartridge.
- [ ] Read NROM PRG/CHR repeatedly and verify byte-for-byte consistency and hashes.
- [ ] Compare against a known-good dump where legally obtained.
- [ ] Implement versioned USB dump transport, mapper-aware bank selection, and safe cartridge RAM handling.

**Pass condition:** repeatable verified NROM dumping. This alone does not prove live-cart console performance.

## Stage 4 — Live-cartridge console and PC viewer

- [ ] Implement 6502 CPU cycles and PPU fetches with actual cartridge read/write timing.
- [ ] Run an NROM cartridge from **live PRG and CHR accesses**, not simply a pre-dumped copy.
- [ ] Implement PPU/CIRAM interaction, APU emulation, host display/audio and controller input.
- [ ] Benchmark actual USB Full Speed payload and frame/audio underruns alongside bus deadlines.

**Pass condition:** a physical NROM game plays normally at real speed using live cartridge accesses.

## Stage 5 — Compatibility and cartridge replacement

- [ ] Support CHR-RAM and real mapper bus writes.
- [ ] Test MMC1 and MMC3 bank switching, M2 / PPU A12 IRQ behavior and cartridge RAM.
- [ ] Ensure RESET retains motherboard RAM while POWER initializes it.
- [ ] Safely test the Tennis → Super Mario Bros. World 9 swap, recording exact steps and limitations.

**Pass condition:** document working mappers and reproducible cartridge tests, not a blanket claim of NES compatibility.

## Stop / pivot rules

- If CPU + PPU + PIO + USB cannot meet measured real-time deadlines, stop before PCB fabrication and reassess pipelining or MCU architecture.
- If the 27-pin design is too fragile, consider a GPIO-richer RP2350B module rather than endlessly adding glue logic.
- If real-time USB video is too costly, test palette/delta/PPU-command protocols and move reconstruction to the host.
- If full live-cart playback stalls, finish a modest and reliable **ROM dumper** instead of expanding scope.

## Next action

**Build and flash the test-only dual-lane PIO loopback firmware on the exact RP2350A Zero.** Verify the two GPIO jumpers and synchronized strobes with a logic analyzer while USB is active. Then replace the serial test lane with an 8-bit latch/transceiver transaction engine and measure deadlines before freezing any cartridge-bus pin map or ordering PCBs.

Related: [development log](journal/2026-10-12.md) · [architecture](architecture.md) · [simulation results](benchmark-results.md) · [PIO bring-up checkpoint](pio-bringup.md).
