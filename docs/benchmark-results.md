# Host-side simulation results

Tested the deterministic Python scheduler locally (16/16 unit tests pass). GitHub Actions status has not been independently verified.

**These are model outcomes, not measured YD-RP2350A / PIO performance.** The model assumes transactions (including addresses and data) are ready and PIO/FIFO/DMA scheduling has no additional stalls.

## Baseline assumptions

- NTSC CPU: 1,789,773 Hz, PPU: 5,369,318 Hz.
- A simulated 262-scanline frame generates 29,781 CPU requests and 40,488 PPU requests.
- Each transaction consumes 12 clocks at 150 MHz plus 22 ns of propagation/settling = 102 ns.
- CPU deadline: 320 ns; PPU deadline: 180 ns (both *assumed*).
- Either separate CPU and PPU engines, or one serialized engine shared by both.

## Results

| Clock | Transaction | Engines | Deadline misses/frame | Worst latency |
| --- | --- | --- | ---: | ---: |
| 150 MHz | 12 cycles + 22 ns | Independent CPU/PPU | 0 | 102 ns |
| 150 MHz | 12 cycles + 22 ns | Shared | 13,496 | 204 ns |
| 150 MHz | 10 cycles + 22 ns | Shared | 0 | 177.3 ns |
| 150 MHz | 24 cycles + 22 ns | Shared | 40,488 | 364 ns |
| 150 MHz | 48 cycles + 22 ns | Independent CPU/PPU | 70,269 | 342 ns |
| 150 MHz | 48 cycles + 22 ns | Shared | 70,269 | ~7.88 ms |

Under the modeled workload, CPU and PPU service windows **overlap 13,496 times** for the 12-cycle independent-engine run. One shared bus thus misses deadlines at the assumed 12-cycle latency. However, the 10-cycle shared configuration passes this simplified model; multiplexing is **not proven impossible**.

## What these results DO NOT establish

- Whether the RP2350 can calculate all CPU and PPU accesses accurately on time.
- Whether the 74-series latch + transceiver control can be implemented in 10–12 PIO clocks.
- Whether the on-board USB and software video encoding fit the CPU budget.
- Whether the RP2350A Zero exposes a workable pin map for the actual Famicom 60-pin connector.
- Whether MMC3 A12/M2 timing, CIRAM, open bus, and cartridge removal work electrically.

## Next test

Build and compile a PIO transaction sequencer, count its instruction cycles and measure real output/input timings on the RP2350A Zero with loopback before designing the cartridge PCB. Replace nominal workloads with recorded/verified 6502/PPU bus traces.
