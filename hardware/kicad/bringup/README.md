# NESPICO Pico 2 8-bit bring-up fixture (draft)

This is a **bench-test fixture**, not the full Famicom cartridge interface and **not a fabrication release**. It exercises two independent 8-bit paths around a standard, non-wireless Raspberry Pi Pico 2:

- **CPU TX:** Pico GP0–GP7 → SN74AHCT245 (A→B, 5 V side) → J3 test header.
- **PPU RX:** J4 5 V-tolerant test header → SN74LVC245A (B→A) → Pico GP8–GP15.
- **Controls:** GP16 drives TX_OE_N; GP17 drives RX_OE_N. Separate 10 kΩ pull-ups keep both active-low enables disabled while the Pico is high impedance.
- **ADC breakout:** GP26–GP28 are analog-only. GP29 is not routed; the Pico 2 uses it internally for VSYS/3 measurement.
- **Power boundary:** USB VBUS powers only the AHCT test buffer. No cartridge power rail or cartridge connector is present. J3/J4 are labelled test-only.

The current rectangular outline is 100 × 82 mm, with two copper layers. The Pico 2 socket rows are 17.78 mm apart and span 48.26 mm. J1/J2 are standard 1×20 socket-strip footprints; confirm the actual socket height and module fit before assembly.

## Pico 2 physical-pin mapping

The local 1×20 connector pad number follows the footprint from top to bottom. With the Pico USB connector at the top, the left side is physical pins 1→20 (`J1`), while the right side is physical pins 40→21 (`J2`). This orientation is checked against Figure 4 of the [Raspberry Pi Pico 2 datasheet](https://pip.raspberrypi.com/documents/RP-008299-DS).

| PCB connector/pad | Pico 2 physical pin | Pico signal | Fixture net / destination |
| --- | ---: | --- | --- |
| J2.1 | 40 | VBUS | +5V_USB, U1 only |
| J2.5 | 36 | 3V3 | +3V3 logic rail |
| J2.7 | 34 | GP28 / ADC2 | J5.1, ADC2_IN |
| J2.8 | 33 | AGND | J5.2, AGND |
| J2.9 | 32 | GP27 / ADC1 | J5.3, ADC1_IN |
| J2.10 | 31 | GP26 / ADC0 | J5.4, ADC0_IN |
| J2.19 | 22 | GP17 | RX_OE_N |
| J2.20 | 21 | GP16 | TX_OE_N |

**J5 order:** `1 ADC2`, `2 AGND`, `3 ADC1`, `4 ADC0`. Keep GP26–GP28 exclusively for analog use in this pin-allocation baseline. **Never drive J5 above 3.3 V or while the Pico is unpowered.** There is no input divider, series protection, or source-conditioning network because the analog source has not been defined; only connect a reviewed 0–3.3 V source with suitable impedance. GP29/ADC3 is internal to the Pico 2 and is not broken out.

## Candidate parts (not a qualified production BOM)

| Reference | Candidate | Footprint | Notes |
| --- | --- | --- | --- |
| U1 | SN74AHCT245DW | SOIC-20W | 5 V supply; fixed A→B; 3.3 V GPIO input meets AHCT VIH under datasheet conditions |
| U2 | SN74LVC245ADW | SOIC-20W | 3.3 V supply; fixed B→A; 5 V-tolerant input under datasheet conditions |
| R1, R2 | 10 kΩ, 0805 | 0805 metric | OE pull-ups; placeholder values |
| C1, C2 | 100 nF, 0805 | 0805 metric | Local bypass placeholders; final placement/value review required |
| J1, J2 | 1×20 female socket strips, 2.54 mm | KiCad standard THT | Check mating height and module fit |
| J3, J4 | 1×10 male pin headers, 2.54 mm | KiCad standard THT | Test-only; not a cartridge connection |
| J5 | 1×4 male pin header, 2.54 mm | KiCad standard THT | ADC-only, 0–3.3 V maximum |

Check the exact orderable component, package suffix, supply/logic limits, bypass layout, and assembly fit against complete datasheets before ordering. The component values are candidates, not a recommendation for a final interface.

## Files and regeneration

- `NESPICO_8bit_fixture.kicad_pro` — KiCad project.
- `NESPICO_8bit_fixture.kicad_sch` — editable schematic.
- `NESPICO_8bit_fixture.kicad_pcb` — editable two-layer PCB.
- `generate_bringup.py` — regenerates the schematic and board using the installed KiCad symbol/footprint libraries.
- `validate_bringup.py` — checks the schematic/PCB pin-net agreement, physical Pico header numbering, ADC reservation, 5 V boundary, and KiCad connectivity.
- `validate_clearance.py` — optional shape-aware, layer-aware 0.20 mm copper spacing screen; requires Shapely in the same Python environment as `pcbnew`.
- `BOM_draft.csv` — unqualified candidate bill of materials; generic connector/passive MPNs remain unselected.
- `references.md` — primary-source device and mechanical references.
- `previews/` — PDF schematic and front/back PCB previews plus SVG layer previews.
- `gerber-draft/` and `NESPICO_8bit_fixture_fab_draft.zip` — provisional Gerber/Excellon outputs for review only.

From the repository root:

```sh
/usr/bin/python3 hardware/kicad/bringup/generate_bringup.py
/usr/bin/python3 hardware/kicad/bringup/validate_bringup.py
# Optional; requires Shapely in the pcbnew Python environment.
/usr/bin/python3 hardware/kicad/bringup/validate_clearance.py
```

The schematic/PCB pin-net validator passes with zero unconnected connections. The optional shape-aware screen checks 130 track/via objects and 112 pads (22,322 relevant pairs) using copper-layer intersections and the actual circle/oval pad shapes; the current result is zero different-net violations below 0.20 mm. The installed KiCad 7 CLI exposes PCB export but not a PCB DRC subcommand; **run the native KiCad DRC and review fabrication outputs on the final candidate before any board order**. Confirm socket/module/mechanical fit and actual electrical behavior on the bench.

## Not included / no release implied

There is no 60-pin cartridge connector, address-latch bank, CIRAM/audio/IRQ logic, cartridge power switching, current limit, reverse-current protection, connector-side ESD network, hot-plug sequence, or final GPIO schedule. The earlier 27-function concept still exceeds the 23 digital external-header GPIOs available when GP26–GP28 are kept for ADC and GP29 remains internal. Those architecture and electrical-safety gates must be resolved before designing or releasing a full cartridge PCB.
