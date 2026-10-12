# Pico 2 board plan and external-logic options

**Status:** a full 60-pin Rev.A functional candidate and a logical GP0–GP22 assignment now exist in [`rev-a-circuit-spec.md`](rev-a-circuit-spec.md) and [`rev_a_logic/`](rev_a_logic/). They are not a frozen electrical design, physical Pico header map, PCB layout, or fabrication release. The separate 8-bit bench fixture is not the complete interface.

## Confirmed project constraints

- Target is a standard, non-wireless Raspberry Pi Pico 2.
- For this design, **GP26–GP28 are reserved for ADC0–ADC2 analog inputs** and will not carry digital cartridge-bus signals. Although these pads can be configured as digital GPIO, doing so would consume the ADC inputs and is outside this pin-allocation baseline.
- **GP29 is ADC3 but is used on the Pico 2 board for VSYS monitoring; it is not an external header GPIO** and is not available to the project.
- The remaining digital header set is **GP0–GP22: 23 pins**. Do not apply cartridge-side 5 V to any RP2350 pad. ADC inputs also need a source-range/impedance review before connection.
- The earlier **27-direct-GPIO concept** is superseded by the Rev.A candidate: address latches and separate bus buffers reduce the proposed Pico map to 23 GPIOs. The candidate map and control/status multiplexing still need PIO scheduling and timing validation before freeze.

| Resource | Count | Project treatment |
| --- | ---: | --- |
| GP0–GP22 | 23 | Digital GPIO budget for the cartridge interface and control |
| GP26–GP28 | 3 | Reserved for ADC0–ADC2; analog-only project routing |
| GP29 | 1 | ADC3/VSYS monitor on Pico 2; no external project connection |
| Prior concept | 27 | Earlier direct-pin idea; superseded, not a confirmed requirement |

## Rev.A candidate logical GPIO partition

To preserve independent CPU/PPU transaction paths, reserve GP0–GP7 and GP8–GP15 as the two byte-wide MCU-side data lanes. The Rev.A candidate assigns the remaining seven digital GPIOs as follows:

| Pico 2 GPIOs | Candidate function | Status |
| --- | --- | --- |
| GP0–GP7 | CPU data lane D0–D7 | Rev.A logical candidate; physical header pads/PIO not validated |
| GP8–GP15 | PPU data lane D0–D7 / wait-state status | Rev.A logical candidate; status returned through mux |
| GP16 | CPU M2 | 5-V AHCT control path |
| GP17 | CPU R/W | 5-V AHCT control path |
| GP18 | PPU /RD | 5-V AHCT control path |
| GP19 | PPU /WR | 5-V AHCT control path |
| GP20 / GP21 | CPU / PPU address strobe | Candidate latch/phase controls |
| GP22 | APU audio PWM | Output to analog boundary; level/filter open |
| GP26–GP28 | ADC0–ADC2 | Reserved, analog only |
| GP29 | ADC3 / VSYS monitor | Pico 2 internal use; never externally routed |

This is a logical candidate map, not a final physical-pin map or firmware contract. Firmware still needs a per-cycle PIO plan for the strobes, byte-latch phase, bus direction and status/IRQ/CIRAM input multiplexing without losing required concurrency.

## External-logic partition candidates

These are candidates to measure and compare, not selected circuits.

### 1. Decode mutually exclusive control strobes

The Rev.A candidate uses local 74-series control logic and independent latches rather than dedicating a Pico GPIO to every address bit. Any encoded strobes must still be mutually exclusive when decoded; CPU and PPU byte lanes remain separate. The global disable must default safe through reset/power faults, and dead time/glitch behavior must be measured before the control equations are frozen.

### 2. Hold address outputs in parallel latch banks

Use byte-wide parallel latch banks to hold CPU and PPU address outputs. Candidate wiring feeds the CPU address latches from the CPU data lane and the PPU address latches from the PPU data lane, temporarily using each lane to load address bytes while its cartridge data transceiver is disabled. This avoids dedicating one Pico pin per address bit and avoids the long serial shift of a 29-bit address, but it adds latch-select cycles and borrows both data lanes during address updates. The exact transaction schedule must be implemented in PIO and checked against measured cartridge timing and CPU/PPU overlap before selecting latch count, control encoding, or footprints.

### 3. Share one CPU/PPU cartridge data lane

This saves GPIOs but serializes transactions that the project currently models as independent CPU and PPU work. In the current synthetic host model, the default serialized configuration misses more than 10,000 deadlines per frame, while a deliberately faster 10-cycle service configuration passes; neither result is a hardware measurement. Do **not** assume this is acceptable for live-cartridge operation without a new worst-case schedule and measurement. It may be a fallback for a deliberately limited ROM-dumper prototype, not a default for the stated live-cart goal.

## Recommended next hardware milestone

Keep the CPU and PPU data paths independent. The next gate is implementing the Rev.A logical GPIO/latch/control sequence in PIO and capturing logic-analyzer traces, including simultaneous CPU/PPU activity, status selection, setup/hold and direction turnaround. If it cannot meet worst-case deadlines, revise the architecture (including a CPLD option) before any full-cartridge PCB.

A separate first bring-up PCB can validate independent 8-bit CPU/PPU buffer paths and ADC-only GP26–GP28 access. A two-lane buffer test fixture now exists in `bringup/`; it is explicitly bench-only and must not imply that the complete 60-pin cartridge interface is ready.

### Bring-up fixture Pico 2 pin-number check

With the Pico USB connector at the top, the J1 left socket row follows physical pins 1–20 from top to bottom, while J2's right socket row follows physical pins 40–21 from top to bottom. Therefore J2.7/8/9/10 map to physical pins 34/33/32/31: GP28/AGND/GP27/GP26. J5 is ordered ADC2/AGND/ADC1/ADC0. GP26–GP28 are analog-only; GP29/ADC3 remains internal for VSYS measurement and is not routed. The repeatable check is `bringup/validate_bringup.py`; device references are in `bringup/references.md`.

## Freeze gates before a full PCB layout

1. Verify the Rev.A candidate's complete GPIO/function list, logical pin use, and Pico physical header mapping; prove the PIO sequence fits the 23-pin budget with GP26–GP28 analog-only and GP29 internal.
2. Verify the selected 60-pin connector part, footprint, card thickness, contact side, and pin numbering; keep cartridge pin 31 isolated until its variant behavior is established. NESdev distinguishes pin 49 `/PPU A13` from pin 56 `PPU A13`; confirm against a real mating target.
3. Select exact orderable logic components and footprints; check 3.3 V input recognition, 5 V output levels, OE behavior, power-off isolation, and propagation against their complete datasheets.
4. Specify cartridge 5 V current limit, inrush, reverse-current protection, power sequencing, reset defaults, and ESD path.
5. Simulate and measure actual latch timing, read/write turnaround, overlapping CPU/PPU requests, and bus contention on the selected Pico 2 and logic.
6. Only after review, replace the functional blocks with a package-level KiCad schematic and checked BOM. PCB layout/fabrication outputs remain deferred; no PCB order or fabrication release is implied.
