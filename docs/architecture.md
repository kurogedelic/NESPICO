# Architecture notes

## Goal

YD-RP2350A Zero + inexpensive 74-series logic + physical 60-pin Famicom cartridge connector. Real cartridge PRG/CHR accesses during emulation, USB ROM dump and USB display/audio/control host. No HDMI, wireless or FPGA. See [README](../README.md).

## Planned signal paths

- Separate CPU and PPU bidirectional 8-bit data paths.
- Independent 74AHCT574 address holding registers, with safe strobes.
- GPIO or PIO control of CPU M2, R/W, /ROMSEL and PPU /RD, /WR.
- Cartridge IRQ, CIRAM control and mapper writes must be supported.
- Verify **every** signal with NESdev cartridge connector pinout before PCB design. The current 27-GPIO idea is **not a validated pin map**.
- The [RP2350 datasheet](https://pip.raspberrypi.com/documents/RP-008373-DS-rp2350-datasheet.pdf) distinguishes standard and FT pads: at IOVDD=3.3 V, FT input tolerance up to 5.5 V is conditional on IOVDD being present and does not establish output compatibility, powered-off safety, or hot-insertion survival. The exact module's pad classes and routing remain unverified. Include OE defaults, transceiver voltage compatibility, ESD, rail sequencing and safe RESET handling in hardware revision.
- A source-checked but explicitly non-final connector inventory is in [the Famicom 60-pin signal register](famicom-60pin-signal-register.md); it leaves GPIO assignment and electrical design open.

## Model's timing assumptions

- NTSC nominal CPU clock: 1,789,773 Hz; PPU dot: 5,369,318 Hz.
- CPU bus request every CPU cycle.
- PPU fetch every two dots during approximate rendering lines; 168 requests/scanline, 241 modelled rendering lines per 262-line frame.
- CPU bus deadline: **assumed** 320 ns; PPU: **assumed** 180 ns.
- Transaction latency: **assumed** 12 RP2350 clocks at 150 MHz, plus 22 ns propagation/settling.
- Two independent hypothetical engines by default; optionally one shared engine for contention stress.
- Neither the workload nor deadlines are an accurate per-dot PPUDATA/CHR/CIRAM transaction trace; real CPU/PPU interleaving, PIO FIFO and DMA behavior require more validation.

With the *assumed* dual-engine parameters, the model reports zero misses; that is **not a silicon benchmark**. The model explicitly cannot determine if real software can calculate the next cartridge address/data fast enough or whether the chosen GPIO multiplexing can serve both buses.

## Tests

```sh
python -m unittest discover -s tests -v
python -m nespico.cli --scanlines 262
python -m nespico.cli --pio-cycles 48 --shared-bus --scanlines 2
```

The last command is an intentionally overloaded shared-engine configuration and should exit nonzero.

## Further simulation before PCB

1. Replace synthetic address streams with a cycle-accurate 6502 execution trace and known PPUs' fetch traces. Verify against NESdev test ROMs.
2. Model all 60-pin signals: M2 high/low phases, simultaneous CPU and PPU transactions, latch strobes, /OE and turnaround/tri-state intervals, mapper IRQ and CIRAM /CE.
3. Add PIO assembly and FIFO/DMA scheduling model with actual proposed GPIO mapping; evaluate worst-case timing and missed deadlines, not averages.
4. Prototype the PIO pattern generator on RP2350A Zero; loopback and a logic analyzer for electrical signal edges.
5. Only then build a 74-series daughterboard for safe NROM PRG/CHR reads, USB dumping and subsequent live-cart tests.

## USB boundary

USB Full Speed has 12 Mbit/s signaling, but lower application payload throughput; 256x240 8-bit frames at 60 fps require about 3.7 MB/s *before* audio and protocol overhead. Use a measured USB transport and experiment with changes/delta data, compressed indexed pixels or PPU commands. Do not assume that a particular compression scheme always fits.
