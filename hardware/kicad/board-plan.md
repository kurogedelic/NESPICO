# Pico 2 board plan and external-logic options

**Status:** design proposal only. This document is not a frozen GPIO map, reviewed schematic, BOM, layout, or fabrication release.

## Confirmed project constraints

- Target is a standard, non-wireless Raspberry Pi Pico 2.
- For this design, **GP26–GP28 are reserved for ADC0–ADC2 analog inputs** and will not carry digital cartridge-bus signals. Although these pads can be configured as digital GPIO, doing so would consume the ADC inputs and is outside this pin-allocation baseline.
- **GP29 is ADC3 but is used on the Pico 2 board for VSYS monitoring; it is not an external header GPIO** and is not available to the project.
- The remaining digital header set is **GP0–GP22: 23 pins**. Do not apply cartridge-side 5 V to any RP2350 pad. ADC inputs also need a source-range/impedance review before connection.
- The repository refers to an earlier **27-GPIO concept**, but does not contain its complete named signal-to-GPIO list. Under this ADC-reserved baseline, at least four functions from that concept must be moved into external logic or eliminated before a project map can be frozen.

| Resource | Count | Project treatment |
| --- | ---: | --- |
| GP0–GP22 | 23 | Digital GPIO budget for the cartridge interface and control |
| GP26–GP28 | 3 | Reserved for ADC0–ADC2; analog-only project routing |
| GP29 | 1 | ADC3/VSYS monitor on Pico 2; no external project connection |
| Prior concept | 27 | Incomplete signal list; short by at least 4 versus GP0–GP22 |

## Provisional direct-pin partition

To preserve the project's independent CPU/PPU transaction paths, reserve the first 16 digital pins as two byte-wide MCU-side data lanes:

| Pico 2 GPIOs | Candidate function | Status |
| --- | --- | --- |
| GP0–GP7 | CPU data lane D0–D7 | Provisional lane allocation; no connector pins or direction/OE function assigned |
| GP8–GP15 | PPU data lane D0–D7 | Provisional lane allocation; no connector pins or direction/OE function assigned |
| GP16–GP22 | 7 remaining control/handshake GPIOs | Function list not assigned; must fit after external decoding |
| GP26–GP28 | ADC0–ADC2 | Reserved, analog only |
| GP29 | ADC3 / VSYS monitor | Pico 2 internal use |

This is a pin-budget partition, not a final GPIO map. Firmware still needs a per-cycle plan for how GP16–GP22 encode PIO strobes, latch selection, bus direction, IRQ, and CIRAM inputs without losing required concurrency.

## External-logic partition candidates

These are candidates to measure and compare, not selected circuits.

### 1. Decode mutually exclusive control strobes

Encode a group of mutually exclusive latch-select/transceiver-enable strobes on a few Pico GPIOs, then decode them locally with 74-series logic. As a concrete count example, eight mutually exclusive functions can be encoded as three select bits plus one valid/enable bit and decoded locally: four direct GPIOs instead of eight, saving four. An 8-output decoder is only an illustrative block, not a selected part. This can reduce MCU pins while keeping CPU and PPU data lanes independent **only if** the decoded functions never need to be active simultaneously. Hold a global disable during code changes and default every cartridge-facing driver off during reset/fault; measured dead time and glitch behavior must be proven. The current 27-signal list is missing, so whether eight suitable functions exist and whether this saves the required four pins are not yet proven.

### 2. Hold address outputs in parallel latch banks

Use byte-wide parallel latch banks to hold CPU and PPU address outputs. Candidate wiring feeds the CPU address latches from the CPU data lane and the PPU address latches from the PPU data lane, temporarily using each lane to load address bytes while its cartridge data transceiver is disabled. This avoids dedicating one Pico pin per address bit and avoids the long serial shift of a 29-bit address, but it adds latch-select cycles and borrows both data lanes during address updates. The exact transaction schedule must be implemented in PIO and checked against measured cartridge timing and CPU/PPU overlap before selecting latch count, control encoding, or footprints.

### 3. Share one CPU/PPU cartridge data lane

This saves GPIOs but serializes transactions that the project currently models as independent CPU and PPU work. In the current synthetic host model, the default serialized configuration misses more than 10,000 deadlines per frame, while a deliberately faster 10-cycle service configuration passes; neither result is a hardware measurement. Do **not** assume this is acceptable for live-cartridge operation without a new worst-case schedule and measurement. It may be a fallback for a deliberately limited ROM-dumper prototype, not a default for the stated live-cart goal.

## Recommended next hardware milestone

Keep the CPU and PPU data paths independent in the first candidate, and evaluate local decoding of mutually exclusive control strobes plus parallel address-holding latches as the GPIO-reduction mechanism. First add the actual 27-function signal list and a proposed 23-pin map; then implement an 8-bit latch/transceiver PIO test and capture logic-analyzer traces. If the test cannot meet worst-case CPU/PPU deadlines, revise the architecture before making a full cartridge PCB.

A separate first bring-up PCB may be useful for the Pico 2, one 8-bit latch/transceiver path, test points, and ADC-only GP26–GP28 access. It must be labelled as a test fixture and must not imply that the complete 60-pin cartridge interface is ready.

## Freeze gates before a full PCB layout

1. Recover and review the complete GPIO/function list and prove it fits the 23-pin budget plus the chosen external logic.
2. Verify the selected 60-pin connector part, footprint, card thickness, contact side, and pin numbering; keep cartridge pin 31 isolated until its variant behavior is established and resolve the pin 49 naming/polarity discrepancy.
3. Select exact orderable logic components and footprints; check 3.3 V input recognition, 5 V output levels, OE behavior, power-off isolation, and propagation against their complete datasheets.
4. Specify cartridge 5 V current limit, inrush, reverse-current protection, power sequencing, reset defaults, and ESD path.
5. Simulate and measure actual latch timing, read/write turnaround, overlapping CPU/PPU requests, and bus contention on the selected Pico 2 and logic.
6. Only after review, generate the full KiCad schematic/PCB, BOM, and fabrication outputs. No PCB order or fabrication release is implied by this proposal.
