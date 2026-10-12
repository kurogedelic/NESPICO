# Rev.A circuit evidence and open constraints

**Status:** circuit research record only. No PCB layout, fabrication data, or production release is created by this note. The user has authorized an initial full-live-cartridge design with CPLD/other programmable logic; PCB work is explicitly deferred until the circuit is fixed.

## User-confirmed hardware baseline

- Target is the standard non-wireless Raspberry Pi Pico 2 and a Famicom 60-pin cartridge interface.
- Preserve separate CPU and PPU 8-bit data lanes.
- **Project allocation rule:** GP26/ADC0, GP27/ADC1 and GP28/ADC2 remain analog inputs only; do not allocate them as digital GPIO. GP29/ADC3 remains reserved for the Pico 2 board's internal VSYS/3 monitor and is not connected externally.
- This leaves GP0–GP22, **23 external digital GPIOs**. The Rev.A logical candidate map is in `rev-a-circuit-spec.md`; the physical Pico 2 header map and firmware contract are not frozen.
- User permits additional CPLD or equivalent programmable logic in the first live-cartridge circuit.

## Source-checked connector facts

- NESdev documents Famicom cartridge contacts at 2.54 mm pitch; pins 01–30 are on the label side (left-to-right in its view), and the opposite 30-contact side is 31–60.
- Pin 31 is revision-dependent: cartridge-present/switch behavior or +5 V. Leave it isolated until the target convention is measured.
- Pin 49 is `/PPU A13` (inverted PPU A13) in the NESdev 60-pin register. Do not silently normalize this as non-inverted PPU A13.
- `/ROMSEL` is the NAND of M2 and CPU A15. Cartridge `/IRQ`, CIRAM A10 and CIRAM `/CE` are cartridge-to-console signals. PPU `/RD` and `/WR` have distinct read/write timing relationships.
- Sullins' official catalog describes a Dual Edge family with 2.54 mm contact centers and 30/60 contact-count chart entry. Its official article describes the family as accepting 1.57 mm boards in both slots. Candidate `EAC30FSLQ` is **not** proven to mate with an actual Famicom cartridge: the exact ordered drawing, card thickness, pad geometry, contact orientation, entry/bevel, keying and sample fit remain open.

## Pico 2 / RP2350 constraints

- Pico 2 GPIO is 3.3 V. GP26–GP28 are ADC-capable header pins; GP29/ADC3 is used on-board to measure VSYS/3. The user has explicitly reserved GP26–28 for ADC use, regardless of their alternate digital capability.
- Pico 2 documentation warns that ADC-capable GPIO input must stay below IOVDD + approximately 0.3 V, and applying a signal while the RP2350 is unpowered may leak through its protection diode. Do not use those pins as a 5 V-tolerant input.
- Pico 2 recommends less than 300 mA external load from its 3V3 pin (actual capacity depends on board load and VSYS). Do not power the cartridge's +5 V rail from Pico 3V3.
- No cartridge-side 5 V signal may be connected directly to an RP2350 GPIO/ADC pin.

## Candidate logic parts — not yet selected

- `ATF1504AS-10JU44` is rejected as the presumed full-bus control device unless a complete pin budget proves otherwise: the official datasheet gives **32 user I/O pins** for the 44-lead PLCC package, not the family-wide `68 inputs/I/O` product summary.
- `ATF1508AS` is the larger Microchip CPLD family candidate. Official datasheet package table: 84-lead PLCC has **64 user I/O**; 100-lead TQFP has **80 user I/O**. The manufacturer page labels the family In Production. Package/pinout, full net budget, exact suffix, supply, configuration method, and availability must be checked before selection.
- Important power caveat: the ATF1508AS standard-power datasheet reports a large standby current (up to 160 mA commercial / 180 mA industrial under its stated test condition). Evaluate the `ASL` low-power variant and other current-production alternatives rather than putting the standard-power part into the circuit by default; its speed grade/timing must still be checked.
- `ATF1508AS-10JU84` is therefore only a research candidate, not a selected circuit part. A 100-TQFP option has more pins but does not cure an unproven protocol or interface budget.

## Candidate 5 V data interface — preliminary

- The initial research considered `SN74AHCT245`/`SN74LVC245A`, but the Rev.A functional design fixes direction per octal path, so its candidate parts are `SN74AHCT244` for Pico-to-cartridge and `SN74LVC244A` for cartridge-to-Pico. TI specifies AHCT VIH(min)=2.0 V at 4.5–5.5 V supply; the LVC244A operates from 1.65–3.6 V, accepts up to 5.5 V inputs, and specifies Ioff/partial-power-down behavior.
- A baseline independent CPU/PPU data interface uses one fixed-direction AHCT244 path and one fixed-direction LVC244A path per 8-bit bus (four data-buffer packages total), with a separate AHCT244 for 5-V control outputs. This remains a candidate topology; OE timing, electrical loading, buffer placement and every signal's ownership need timing review.
- AHCT `/OE` is active-low. Its safe-default pull-up is to the AHCT supply (5 V); do not connect a 5 V `/OE` pull-up directly to a Pico GPIO. Control-level translation must be designed explicitly.

## Candidate protection / power blocks — not values-frozen

- `TPS25940A` is a candidate eFuse for the separate cartridge +5 V power path: adjustable current limit, soft-start/dV/dt control and reverse-current blocking are stated in TI's datasheet. Cartridge current and inrush have not been measured; **do not assign an ILIM value yet**. Define the upstream 5 V source, USB/VBUS isolation, rail sequencing, reset default-off and thermal limits.
- Low-capacitance 5 V-class ESD arrays such as TI `TPD4E05U06` or Infineon `ESD5V3U4U-HDMI` are candidates at connector-exposed signal groups. A 5–5.5 V working standoff does not imply a clamp safe for a 3.3 V RP2350 pin; confirm the complete clamp waveform and the protected IC's limits. ESD devices do not replace power-path current/reverse protection.
- Connector-side signal/audio protection and short return layout still require circuit-level review; IEC component ratings alone are not board-level validation.

## ADC / audio candidates — values intentionally open

- GP26/ADC0 may be used to observe cartridge audio returning on Famicom pin 46 (`Audio to RF`); this is only a candidate assignment. The signal's max/min amplitude, DC offset, source impedance, bandwidth and cartridge-to-cartridge variation are not known.
- GP27/ADC1 and GP28/ADC2 remain available for analog sensing/auxiliary inputs after their signal sources are defined. GP29 remains internal.
- No ADC pin may be wired straight to pin 45/46 or a 5 V rail. Determine whether AC coupling, ADC-side bias, divider, series impedance, buffer and anti-alias filtering are required only after measuring the source; do not invent resistor/capacitor values now.
- Famicom pin 45 is audio from the 2A03 toward the cartridge; pin 46 returns the mixed audio toward the console. A waveform generator/output filter for pin 45 also needs a defined amplitude, bias, output impedance and audio-band target.

## Primary references

1. NESdev Wiki, “Cartridge connector” — pinout, 2.54 mm pitch, pin 31 variant note, signal directions, `/ROMSEL`, `/PPU A13`, CIRAM and audio roles: https://www.nesdev.org/wiki/Cartridge_connector
2. Raspberry Pi Pico 2 Datasheet — header/ADC allocation, GP29 VSYS/3, ADC input and unpowered-leakage warning, 3V3 load note: https://pip.raspberrypi.com/documents/RP-008299-DS
3. Raspberry Pi RP2350 Datasheet — pad, PIO, ADC and electrical limits: https://pip.raspberrypi.com/documents/RP-008373-DS-rp2350-datasheet.pdf
4. Microchip ATF1504AS(L) Datasheet — package-specific `# User I/O Pins` and electrical/timing details: https://ww1.microchip.com/downloads/aemDocuments/documents/MPD/ProductDocuments/DataSheets/ATF1504AS%28L%29-5V-64-Macrocell-CPLD-Data-Sheet-20006580A.pdf
5. Microchip ATF1508AS(L) Datasheet — package-specific I/O counts, power and timing: https://ww1.microchip.com/downloads/en/DeviceDoc/ATF1508AS(L)-5V-128-Macrocell-CPLD-Data-Sheet-20006682A.pdf
6. Microchip ATF1508AS product page — production status and current manufacturer catalog snapshot: https://www.microchip.com/en-us/product/atf1508as
7. TI SN74AHCT244 Datasheet — Rev.A fixed-direction 5 V buffer, input thresholds, /OE and timing: https://www.ti.com/lit/ds/symlink/sn74ahct244.pdf . SN74AHCT245 (DIR-capable) is used by the separate one-bit/8-bit bring-up fixtures: https://www.ti.com/lit/ds/scls233p/scls233p.pdf
8. TI SN74LVC244A Datasheet — Rev.A fixed-direction 3.3 V buffer, 5.5 V inputs, Ioff, /OE and timing: https://www.ti.com/lit/ds/symlink/sn74lvc244a.pdf . SN74LVC245A applies to the separate bring-up fixture: https://www.ti.com/lit/gpn/SN74LVC245A
9. Sullins 2019 Catalog — Dual Edge connector family and mechanical drawings: https://www.sullinscorp.com/wp-content/uploads/2018/10/2019-CATALOG.pdf
10. Sullins Dual Edge announcement — 2.54 mm family pitch and 1.57 mm mating board statement: https://www.sullinscorp.com/news/news-releases/dual-edge-connectors-now-available-from-sullins-connector-solutions/
11. TI TPS25940A/TPS25940L Datasheet — current-limit and reverse-blocking candidate: https://www.ti.com/lit/ds/slvscf3/slvscf3.pdf
12. TI TPD4E05U06 Datasheet — candidate signal ESD array: https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf
13. Infineon ESD5V3U4U-HDMI Datasheet — alternative candidate signal ESD array: https://www.infineon.com/dgdl/esd5v3u4u-hdmi.pdf?folderId=db3a30431441fb5d011488a9e66f0ded&fileId=db3a30431ce5fb52011d4d0e9b312dd0

## Circuit-freeze gates

1. Review the Rev.A signal-by-signal netlist and GP0–GP22 logical pin budget; verify physical Pico 2 header mapping and the firmware/PIO ownership contract.
2. Implement and measure the control/clock protocol so independent CPU and PPU addresses, reads, writes, data-buffer OEs and bus turnarounds work without contention. Include IRQ/CIRAM feedback to the Pico.
3. Keep the current discrete-AHCT candidate only if measured PIO timing and bus concurrency pass; if they fail, budget the CPLD package/power/programming interface as the documented fallback.
4. Confirm an exact 60-pin receptacle drawing and physical cartridge mating sample; keep pin 31 NC until checked.
5. Measure representative cartridge power, analog audio and bus timing; then set current limit, ADC conditioning and wait/deadtime values.
6. Only after the above, mark the native schematic electrically complete. PCB layout/Gerber production remains explicitly deferred.


## Additional primary-source checks (2026-10-12)

- Microchip’s official `ATF1508ASL` product page labels the family **In Production / Low Power** and lists `ATF1508ASL-25JU84` (84-lead PLCC) and `ATF1508ASL-25AU100` (100-lead TQFP). The official family datasheet gives **64 user I/O** in 84-PLCC and **80 user I/O** in 100-TQFP. The low-power `-25` order-code grade has a 25 ns input-to-nonregistered-output maximum and 70 MHz fMAX in the ordering table. It is a plausible candidate, not yet selected; programming equipment and exact I/O budget remain open.
- TI `SN74AHCT573` is an octal transparent D latch: LE high follows D, LE low stores; OE is active-low and high-Z at high. TI recommends a pull-up to VCC for high-Z during power-up/down. With VCC 4.5–5.5 V, VIH(min)=2.0 V; TI specifies up to 5.5 V inputs. Its setup/hold requirement is 3.5/1.5 ns and tpd LE→Q is up to 10.5 ns at the cited 50 pF load. This supports (but does not yet validate) Pico-3.3V-to-5V latch input compatibility.
- TI `SN74AHCT74` is a dual positive-edge D flip-flop with asynchronous active-low PRE/CLR, 4.5–5.5 V operation and TTL-compatible inputs. Any address-byte phase/toggle circuit must be simulated and reset-tested before it is frozen.
- TI `SN74LVC257A` runs from 1.65–3.6 V, accepts inputs up to 5.5 V, and has active-low output enable with tri-state outputs. TI specifies maximum tpd 4.6 ns at 3.3 V. This is a candidate for time-multiplexing cartridge IRQ/CIRAM status into a Pico-side data lane, with output OE held high when the Pico lane is driven.
- NESdev’s expansion-audio category and the cross-check article describe the cartridge as mixing incoming 2A03 audio with cartridge-generated audio; pin 46 returns the mixed signal. These sources establish signal direction and purpose, **not** an electrical amplitude, DC bias, source/load impedance or ADC-safe range. Pin 45/46 analog values remain an explicit measurement gate.
- An early attempt to fetch an obsolete Alliance Memory URL returned a generic site page. This was superseded by the successful official datasheet fetch and pinout review recorded below; it is not evidence against the verified PDF.

Additional sources:

14. Microchip ATF1508ASL official product page: https://www.microchip.com/en-us/product/atf1508asl
15. TI SN74AHCT573 datasheet: https://www.ti.com/lit/ds/symlink/sn74ahct573.pdf
16. TI SN74AHCT74 datasheet: https://www.ti.com/lit/ds/symlink/sn74ahct74.pdf
17. TI SN74LVC257A datasheet: https://www.ti.com/lit/ds/symlink/sn74lvc257a.pdf
18. NESdev Wiki, Expansion audio: https://www.nesdev.org/wiki/Category:Expansion_audio
19. J. S. Groth, Famicom Expansion Audio: https://jsgroth.dev/blog/posts/famicom-expansion-audio/

- An early search found the official AS6C6264 page and PDF links; that lead was superseded by opening and reviewing the complete manufacturer datasheet below.
- Opened Alliance Memory’s official AS6C6264 datasheet (`Alliance-Memory_64K_AS6C6264v2.0July2017.pdf`). The device is 8K×8, 2.7–5.5 V, 55 ns; it has active-low CE#, OE#, WE# and a separate active-high CE2. The candidate `AS6C6264-55PCN` (28-pin PDIP, commercial) is listed in the official part table. Its pinout was visually checked and encoded in the KiCad symbol; current topology checks confirm CE#/A10 routing and PPU A10 separation, but do not assert every SRAM pin. Exact sourcing/package/footprint and a full pin-by-pin audit remain open. Source: https://www.alliancememory.com/wp-content/uploads/Alliance-Memory_64K_AS6C6264v2.0July2017.pdf
- NESdev’s current Famicom connector table resolves the apparent PPU A13 duplicate: pin 49 is **PPU /A13** (inverted), pin 56 is **PPU A13** (non-inverted). This is not a duplicate net and needs one inversion. The source also states /ROMSEL is NAND(M2, CPU A15), with CPU A15 otherwise unavailable as a pin. Source: https://www.nesdev.org/wiki/Cartridge_connector
- TI confirms the `SN74AHCT245` accepts 3.3 V logic at 5 V supply (VIH(min)=2.0 V), has active-low OE and fixed direction selected by DIR; `SN74LVC245A` operates 1.65–3.6 V, accepts 5.5 V inputs and supports Ioff for partial-power-down/back-drive protection. Sources: https://www.ti.com/lit/ds/symlink/sn74ahct245.pdf and https://www.ti.com/lit/ds/symlink/sn74lvc245a.pdf


## 2026-10-12 — CIRAM direction and control-logic sources

- NESdev, [Cartridge connector](https://www.nesdev.org/wiki/Cartridge_connector), fetched 2026-10-12. The page states that signal descriptions are from the console's viewpoint. Pin 18 `CIRAM A10` is an input to the console (cartridge-to-console); it is the mapper-selected 1 KiB bank bit for the console's internal VRAM. The page says horizontal mirroring may connect CIRAM A10 to PPU A10, vertical mirroring to PPU A11, while mapper-controlled mirroring can multiplex/latch either. Pin 48 `/CE` and pin 15 `/IRQ` are also cartridge-driven toward the console. NESPICO is the console/host, so its direction register is authoritative for this design.
- TI, [SN74AHCT00 datasheet](https://www.ti.com/lit/ds/symlink/sn74ahct00.pdf), fetched 2026-10-12. The SN74AHCT00 is a quad 2-input positive-NAND with TTL-compatible inputs; the 14-pin D/DB/DGV/N/NS/PW pin table is captured in the source. Candidate for active-low selects and OE control.
- TI, [SN74AHCT04 datasheet](https://www.ti.com/lit/ds/symlink/sn74ahct04.pdf), fetched 2026-10-12. The SN74AHCT04 contains six independent inverters; TI states AHCT inputs accept 2 V VIH and support 3.3-to-5 V up-translation. Candidate for PPU A13 inversion, strobe/control complements, and safe-enable logic.
- TI, [SN74AHCT08 datasheet](https://www.ti.com/lit/ds/symlink/sn74ahct08.pdf), fetched 2026-10-12. The SN74AHCT08 is a quad 2-input positive-AND; TI lists 4.5–5.5 V supply, VIH(min)=2 V, VIL(max)=0.8 V and input range to 5.5 V. Candidate for BUS_RUN, bus-cycle qualification and latch-enable generation.
- TI, [SN74AHCT244 datasheet](https://www.ti.com/lit/ds/symlink/sn74ahct244.pdf), fetched 2026-10-12. The SN74AHCT244 operates at 4.5–5.5 V, has VIH(min)=2 V, accepts inputs to 5.5 V, and has two active-low output enables. Maximum A→Y delay is 8.5 ns at 15 pF and 9.5 ns at 50 pF in the specified table conditions; this supports 3.3-V Pico logic input but is not a bus timing proof.
- TI, [SN74LVC244A datasheet](https://www.ti.com/lit/ds/symlink/sn74lvc244a.pdf), fetched 2026-10-12 (revision June 2026). It operates at 1.65–3.6 V, accepts inputs to 5.5 V, and specifies Ioff for 5.5-V partial-power-down conditions; it has two active-low output enables. At 3.3-V supply its maximum data delay is 5.9 ns under the cited temperature/load conditions. This is not a board-level sequencing or timing sign-off.
- These are device-family candidates, not a sourcing commitment, package selection, timing proof, or permission to fabricate. Actual series/package propagation, decoupling, unused-gate handling and reset pulls still require review.


## Rev.A functional-circuit update (2026-10-12)

- The user chose to defer the PCB and fix the circuit first; the user allows external logic but has not required that it be a CPLD. Rev.A starts with discrete AHCT logic, with a CPLD still a fallback if measured PIO timing/throughput fails.
- Logical Pico boundary J1 is now pin 1=GP0 through pin 23=GP22. GP26/ADC0–GP28/ADC2 are analog-only on J2; GP29 is not routed; GP23 is not part of the standard Pico 2 external GPIO budget.
- Functional logic protects both borrowed byte lanes: each CPU/PPU address strobe disables its corresponding TX/RX buffers; CPU address load forces M2 low, R/W high and /ROMSEL high; PPU address load forces /RD and /WR high. The status mux drives GP8–GP15 only during safe PPU idle, never during PPU read/write/address load. SRAM /OE and /WE share PPU receive/transmit enable nets.
- A candidate DIP14 control-gate pin assignment is recorded in `rev-a-circuit-spec.md`; it uses 4× SN74AHCT08 (14/16 gates), 2× SN74AHCT00 (7/8), and 2× SN74AHCT04 (9/12). These are candidate package pinouts, not approved order codes or verified KiCad gate-unit placements.
- Rev.A v0.3 A3 PDF was regenerated after a visual pass removed overlapping abstract-block pin names and header labels. The design is console/host-side: pin 44 `/ROMSEL` correctly remains an output generated from M2 and latched CPU A15.
- Latest export passes the netlist topology validator at 133 nets/412 nodes and the Boolean checker at 527 assertions. KiCad schematic ERC, electrical/timing review, PIO and powered-hardware tests are not available from these results.
- Still open: exact orderable/package confirmation, reset pulls and 5-V power/current/sequence protection, analog audio conditioning and safe ADC range, cartridge connector mating/variant, PIO turnaround/setup-hold measurements. No PCB was started.
