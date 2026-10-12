# Host-side simulation results

The original deterministic Python scheduler baseline passed 21/21 tests; its initial GitHub Actions status had not been independently verified at that time. Current verification is recorded in the development log.

**These are model outcomes, not measured Raspberry Pi Pico 2 / PIO performance.** The model assumes transactions (including addresses and data) are ready and PIO/FIFO/DMA scheduling has no additional stalls.

## Baseline assumptions

- NTSC CPU: 1,789,773 Hz, PPU: 5,369,318 Hz.
- A simulated 262-scanline frame generates 29,781 approximate CPU-cycle slots and 40,970 PPU fetch slots: 170 per rendering scanline on visible lines 0–239 and pre-render line 261.
- Each transaction consumes 12 clocks at 150 MHz plus 22 ns of propagation/settling = 102 ns.
- CPU deadline: 320 ns; PPU deadline: 180 ns (both *assumed*).
- Either separate CPU and PPU engines, or one serialized engine shared by both.
- PPU slot phases are classified from [NESdev's PPU rendering timing](https://www.nesdev.org/wiki/PPU_rendering); the addresses, render-enable state, actual sprite contents, and CPU bus addresses are not generated. Treat this as a timing-slot model, not a complete bus trace.

## Results

| Clock | Transaction | Engines | Deadline misses/frame | Worst latency |
| --- | --- | --- | ---: | ---: |
| 150 MHz | 12 cycles + 22 ns | Independent CPU/PPU | 0 | 102 ns |
| 150 MHz | 12 cycles + 22 ns | Shared | 13,657 | 204 ns |
| 150 MHz | 10 cycles + 22 ns | Shared | 0 | 177.3 ns |
| 150 MHz | 24 cycles + 22 ns | Shared | 40,970 | 364 ns |
| 150 MHz | 48 cycles + 22 ns | Independent CPU/PPU | 70,751 | 342 ns |
| 150 MHz | 48 cycles + 22 ns | Shared | 70,751 | ~8.04 ms |

Under the modeled workload, CPU and PPU service windows **overlap 13,657 times** for the 12-cycle independent-engine run. One shared bus thus misses deadlines at the assumed 12-cycle latency. However, the 10-cycle shared configuration passes this simplified model; multiplexing is **not proven impossible**.

## What these results DO NOT establish

- Whether the RP2350 can calculate all CPU and PPU accesses accurately on time.
- Whether the 74-series latch + transceiver control can be implemented in 10–12 PIO clocks.
- Whether the on-board USB and software video encoding fit the CPU budget.
- Whether the standard Pico 2's 26 exposed header GPIOs, combined with external latches/transceivers, can support a workable Famicom 60-pin interface.
- Whether MMC3 A12/M2 timing, CIRAM, open bus, and cartridge removal work electrically.

## Next test

Build and compile a PIO transaction sequencer, count its instruction cycles and measure real output/input timings on Raspberry Pi Pico 2 with loopback before designing the cartridge PCB. Replace nominal workloads with recorded/verified 6502/PPU bus traces.

## Follow-up: request preparation cost

Added `nespico/pipeline.py` and `tests/test_pipeline.py`. This is a deliberately **conservative model with no lookahead**: the CPU/PPU must prepare an address before its PIO bus transaction. It still assumes zero DMA/FIFO setup overhead.

At 150 MHz, with the same **assumed** 12 bus clocks + 22 ns settling, 320 ns CPU and 180 ns PPU deadlines:

| CPU preparation | PPU preparation | CPU misses/frame | PPU misses/frame |
|---:|---:|---:|---:|
| 0 cycles | 0 cycles | 0 | 0 |
| 10 cycles | 10 cycles | 0 | 0 |
| 30 cycles | 10 cycles | 0 | 0 |
| 40 cycles | 10 cycles | 29,781 | 0 |
| 10 cycles | 12 cycles | 0 | 40,970 |
| 10 cycles | 16 cycles | 0 | 40,970 |

One full NTSC-like simulated frame contains 29,781 CPU-cycle slots and 40,970 PPU fetch slots. **These numbers are NOT measured MCU performance and the events are not address-accurate.** Computation may be pipelined earlier, but real instruction emulation, PPU address generation, DMA FIFO delivery, USB interrupts and jitter may cost considerably more. This shows why merely getting zero deadline misses in the original bus-only timing model does not justify fabricating a PCB.

**Go/no-go:** Continue host software and Pico 2 PIO timing development. Do not freeze a GPIO map or order the two cartridge PCBs until (1) an actual PIO instruction sequence exists, (2) per-access producer budgets are measured or bounded on RP2350, (3) the 27-signal concept is reconciled with Pico 2's 26 exposed header GPIOs, and (4) the CPU/PPU bus and 5 V electrical interface are reviewed.
