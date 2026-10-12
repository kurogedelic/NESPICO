# Famicom 60-pin signal register (draft)

**Status:** source-checked signal inventory; **not** a schematic, validated pin map, or approval to fabricate. This records the connector-level interface for NESPICO acting as a console/host and a physical cartridge attached. It assigns no RP2350 GPIOs and selects no interface ICs.

## Numbering and direction convention

The pin numbers below follow the top-down view looking into the 60-pin connector documented by [NESdev's Cartridge connector page](https://www.nesdev.org/wiki/Cartridge_connector): pins 01–30 are on the cartridge-label side, left to right; pins 31–60 are on the opposite side, left to right. The footprint drawing, contact side, and numbering orientation of the exact connector still must be checked before CAD layout.

Direction is from **NESPICO-as-console at the connector**:

- **OUT**: driven by NESPICO toward the cartridge.
- **IN**: driven by the cartridge toward NESPICO.
- **BIDIR**: ownership changes by transaction; this does not imply that a direct MCU connection is safe.
- **PWR**: power rail, not a logic signal.
- **GND**: return.
- **UNRESOLVED**: variant-dependent or not yet assigned safely.

The source diagram and descriptions mostly use the console's viewpoint. The source explicitly notes that pin 31 may be a cartridge-present/contact function or +5 V depending on Famicom RF-board revision; do not assume a universal connection.

## Complete connector register

| Pin | Signal | NESPICO direction / class | Function and review note |
| ---: | --- | --- | --- |
| 01 | GND | GND | Ground return. |
| 02 | CPU A11 | OUT | CPU address bus; level/interface and timing TBD. |
| 03 | CPU A10 | OUT | CPU address bus; level/interface and timing TBD. |
| 04 | CPU A9 | OUT | CPU address bus; level/interface and timing TBD. |
| 05 | CPU A8 | OUT | CPU address bus; level/interface and timing TBD. |
| 06 | CPU A7 | OUT | CPU address bus; level/interface and timing TBD. |
| 07 | CPU A6 | OUT | CPU address bus; level/interface and timing TBD. |
| 08 | CPU A5 | OUT | CPU address bus; level/interface and timing TBD. |
| 09 | CPU A4 | OUT | CPU address bus; level/interface and timing TBD. |
| 10 | CPU A3 | OUT | CPU address bus; level/interface and timing TBD. |
| 11 | CPU A2 | OUT | CPU address bus; level/interface and timing TBD. |
| 12 | CPU A1 | OUT | CPU address bus; level/interface and timing TBD. |
| 13 | CPU A0 | OUT | CPU address bus; level/interface and timing TBD. |
| 14 | CPU R/W | OUT | High during CPU reads, low during writes; source says mode changes while M2 is low. |
| 15 | `/IRQ` | IN | Active-low cartridge interrupt. Treat as a shared/open-drain-style line; do not drive high push-pull. Pull-up and interface design TBD. |
| 16 | GND | GND | Ground return. |
| 17 | PPU `/RD` | OUT | Active-low PPU read strobe. |
| 18 | CIRAM A10 | IN | Cartridge/mapper-selected address bit for the console's internal CIRAM path. Ownership and memory topology TBD. |
| 19 | PPU A6 | OUT | PPU address bus. |
| 20 | PPU A5 | OUT | PPU address bus. |
| 21 | PPU A4 | OUT | PPU address bus. |
| 22 | PPU A3 | OUT | PPU address bus. |
| 23 | PPU A2 | OUT | PPU address bus. |
| 24 | PPU A1 | OUT | PPU address bus. |
| 25 | PPU A0 | OUT | PPU address bus. |
| 26 | PPU D0 | BIDIR | PPU data bus; cartridge drives during reads, NESPICO drives during writes. Direction/OE turnaround must be enforced. |
| 27 | PPU D1 | BIDIR | Same shared-bus ownership rule as PPU D0. |
| 28 | PPU D2 | BIDIR | Same shared-bus ownership rule as PPU D0. |
| 29 | PPU D3 | BIDIR | Same shared-bus ownership rule as PPU D0. |
| 30 | +5V | PWR → cartridge | Cartridge supply contact. Current budget, switch/current limit, inrush, reverse/short protection, and power sequencing are all TBD. Never source this from an MCU GPIO. |
| 31 | Cartridge-present / +5V (variant-dependent) | UNRESOLVED | NESdev documents RF-board variants. Keep isolated/NC in the draft design until the target convention and connector-side behavior are deliberately selected and checked. Do not hard-wire to pin 30 by assumption. |
| 32 | M2 | OUT | CPU clock/phase output. Address and R/W are valid while M2 is high per the cited signal description. |
| 33 | CPU A12 | OUT | CPU address bus. |
| 34 | CPU A13 | OUT | CPU address bus. |
| 35 | CPU A14 | OUT | CPU address bus. |
| 36 | CPU D7 | BIDIR | CPU data bus; ownership follows read/write phase and address decoding. Direction/OE turnaround TBD. |
| 37 | CPU D6 | BIDIR | Same shared-bus ownership rule as CPU D7. |
| 38 | CPU D5 | BIDIR | Same shared-bus ownership rule as CPU D7. |
| 39 | CPU D4 | BIDIR | Same shared-bus ownership rule as CPU D7. |
| 40 | CPU D3 | BIDIR | Same shared-bus ownership rule as CPU D7. |
| 41 | CPU D2 | BIDIR | Same shared-bus ownership rule as CPU D7. |
| 42 | CPU D1 | BIDIR | Same shared-bus ownership rule as CPU D7. |
| 43 | CPU D0 | BIDIR | Same shared-bus ownership rule as CPU D7. |
| 44 | `/ROMSEL` | OUT | Active-low NAND of M2 and CPU A15; the connector signal supplies the otherwise unavailable A15 decode information. |
| 45 | Audio from 2A03 | OUT (analog) | Console audio input to cartridge for mixing. Analog coupling, bias, impedance, and protection TBD; not a GPIO. |
| 46 | Audio to RF | IN (analog) | Cartridge-mixed audio returned to console. Analog front end and host audio path TBD; not a GPIO. |
| 47 | PPU `/WR` | OUT | Active-low PPU write strobe. Source says address and data are stable at its falling edge. |
| 48 | CIRAM `/CE` | IN | Cartridge/mapper-controlled active-low enable for internal CIRAM. Mapping and electrical ownership TBD. |
| 49 | PPU `/A13` (source naming discrepancy) | OUT | NESdev labels this the inverted form of PPU A13; a second pinout source abbreviates it as PPU A13 without the slash. Confirm against a primary schematic/real board before committing polarity or net name. |
| 50 | PPU A7 | OUT | PPU address bus. |
| 51 | PPU A8 | OUT | PPU address bus. |
| 52 | PPU A9 | OUT | PPU address bus. |
| 53 | PPU A10 | OUT | PPU address bus. |
| 54 | PPU A11 | OUT | PPU address bus. |
| 55 | PPU A12 | OUT | PPU address bus. |
| 56 | PPU A13 | OUT | PPU address bus. Distinct connector signal from pin 49 as listed by NESdev. |
| 57 | PPU D7 | BIDIR | Shared PPU data bus; direction/OE turnaround TBD. |
| 58 | PPU D6 | BIDIR | Same shared-bus ownership rule as PPU D7. |
| 59 | PPU D5 | BIDIR | Same shared-bus ownership rule as PPU D7. |
| 60 | PPU D4 | BIDIR | Same shared-bus ownership rule as PPU D7. |

## Timing facts captured for later budgeting

These are protocol-level notes from the NESdev signal descriptions, not complete setup/hold specifications or measured timing limits:

- CPU address and R/W are valid while M2 is high; R/W changes mode only while M2 is low. For CPU reads and writes, data is only guaranteed/required valid at the falling edge of M2.
- PPU `/WR`: address and data are stable at the falling edge.
- PPU `/RD`: address is stable at its falling edge; read data should remain stable until its rising edge.
- These relationships must be mapped to RP2350 PIO strobes, latch enables, transceiver direction, `/OE`, and explicit dead time. Component propagation, cartridge loading, and the exact timing margins remain unmeasured.

## Electrical and architecture holds

1. **No direct RP2350-to-cartridge bus wiring is approved by this register.** Select buffers/transceivers only after checking the exact MCU module, supply domain, pin limits, guaranteed input/output thresholds, loading, and powered-off behavior against the relevant datasheets. On standard Pico 2, GP26–GP28 are ADC-capable header GPIOs with an input diode to IOVDD; keep them within the 3.3 V domain and do not drive them while the MCU is unpowered. GP29 is used on-board for VSYS/3 measurement and is not a header GPIO.
   The RP2350 datasheet distinguishes standard and fault-tolerant (FT) pads: at IOVDD=3.3 V it lists a standard-pad absolute maximum of IOVDD+0.5 V, while an FT pad is listed up to 5.5 V only with IOVDD present. Its electrical table lists FT VIH(min)=2.0 V and GPIO VOH(min)=2.62 V at IOVDD=3.3 V under the stated drive-current conditions. These are chip-level limits, not a universal 5 V interface guarantee: the exact pad class and module routing are unverified, FT voltage tolerance does not establish powered-off/hot-plug safety, and the output HIGH is not guaranteed to satisfy every 5 V receiver.
2. Hold all bus transceiver `/OE` controls in a safe disabled state during reset, boot, fault, and cartridge insertion/removal; prove there is no opposing drive during CPU/PPU read/write turnaround.
3. Provide a separately reviewed 5 V cartridge rail at pin 30. Establish current, inrush, short-circuit and reverse-current limits plus rail sequencing before connecting a real cartridge.
4. Keep pin 31 isolated until the intended cartridge-present convention is established. A pinout drawing from one console revision is not a substitute for continuity measurements on the selected hardware.
5. Keep the analog audio path separate from the digital level-translated bus. CIRAM A10 and `/CE` require an explicit ownership decision and must not be treated as ordinary GPIOs without a complete path review.
6. No per-pin GPIO allocation, latch/transceiver part number, final 27-GPIO map, voltage guarantee, full timing budget, schematic, BOM, or fabrication release is implied.

## Outstanding decisions

- Verify the exact 60-pin connector part, footprint drawing, card thickness/contact dimensions, and pin numbering/orientation.
- Resolve pin 31 behavior and independently verify the pin 49 PPU A13 polarity/name on a primary hardware reference.
- Decide how CPU/PPU address latches, bidirectional data buffers, bus ownership, reset defaults, CIRAM, IRQ, and analog audio are implemented.
- Assign the project signals against the standard Pico 2's 26 header GPIOs (GP0–GP22, GP26–GP28), reserving board-internal GP23/24/25/29 and USB/debug/boot functions as needed. The earlier 27-GPIO concept exceeds the available header GPIO count and must be reduced or offloaded to external logic.
- Derive quantitative timing and electrical constraints from selected component datasheets and actual bus measurements before schematic review or PCB release.

## Sources

- [NESdev Wiki — Cartridge connector](https://www.nesdev.org/wiki/Cartridge_connector), accessed 2026-10-12. Primary reference for the 60-pin diagram, console-viewpoint directions, pin 31 revision note, and signal behavior summaries.
- [ConsoleMods Wiki — Connector Pinouts](https://consolemods.org/wiki/NES:Connector_Pinouts), accessed 2026-10-12. Cross-check for pin numbers, connector-side numbering convention, and audio direction; it abbreviates pin 49 as PPU A13, so polarity remains an open verification item rather than being silently normalized.
- [Raspberry Pi — RP2350 Datasheet](https://pip.raspberrypi.com/documents/RP-008373-DS-rp2350-datasheet.pdf) and [Hardware design with RP2350](https://pip.raspberrypi.com/documents/RP-008280-DS-hardware-design-with-rp2350.pdf), accessed 2026-10-12. Required primary references for later GPIO, module, power, and board-level review; no pin-level voltage guarantee is asserted here.
- [Raspberry Pi — Pico 2 Datasheet](https://pip.raspberrypi.com/documents/RP-008299-DS), accessed 2026-10-12. Primary source for the Pico 2 header GPIO set, board-internal GPIO functions, and ADC-capable input caveat.
