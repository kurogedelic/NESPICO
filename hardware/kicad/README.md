# KiCad: preliminary one-bit interface slice

This is a **candidate topology sketch**, not a complete interface schematic and not released for fabrication. It connects only the D0 lane:

- U1 `SN74AHCT244`: RP2350-side `MCU_D0` input to 5-V-side `CART_D0` output.
- U2 `SN74LVC244A`: 5-V-side `CART_D0` input to RP2350-side `MCU_D0` output. The candidate LVC device's input range permits 5-V signals when operated within its datasheet conditions; the schematic does not claim power-off or hot-plug safety for the whole system.
- `TX_OE_N` and `RX_OE_N` are separate, active-low outputs with 10 kΩ pull-ups to `+3V3_LOGIC`, so both buffers default disabled while the controller is high impedance. The remaining OE sections are held inactive.
- All unused 244 inputs are tied low, unused outputs are explicitly no-connect, and one 100 nF bypass placeholder is shown for each IC.

## Files

- `NESPICO_Interface.kicad_pro` — open this project file in KiCad.
- `NESPICO_Interface.kicad_sch` — editable native schematic.
- `NESPICO_Interface.kicad_sym` and `sym-lib-table` — project-local candidate symbols.
- `NESPICO_Interface.pdf` / `svg/NESPICO_Interface.svg` — generated visual previews.
- `NESPICO_Interface.net` — KiCad-exported connectivity snapshot.
- `generate_preliminary.py` — regenerates the local symbol library and schematic using installed KiCad standard library symbols.
- `validate_preliminary.py` — independently exports KiCad XML netlist and asserts the D0 path, enable nets, supply/GND ties, and NC outputs.
- `board-plan.md` — GP26–GP28 ADC reservation, 23-pin budget, and candidate external-logic partitions; not a frozen design.

From the repository root:

```sh
python3 hardware/kicad/generate_preliminary.py
python3 hardware/kicad/validate_preliminary.py
kicad-cli sch export pdf hardware/kicad/NESPICO_Interface.kicad_sch -o hardware/kicad/NESPICO_Interface.pdf
```

The generation script expects a KiCad installation whose standard symbol files live under `/usr/share/kicad/symbols`; the checked-in schematic and local library are ordinary KiCad files and remain available independently of rerunning the generator.

## Separate 8-bit Pico 2 bring-up fixture

The separate [`bringup/`](bringup/README.md) project is an editable two-layer test fixture for independent CPU-TX and PPU-RX byte lanes. It reserves GP26–GP28 for ADC0–ADC2, leaves GP29 internal, and marks the 5 V-side headers as test-only. Its ADC breakout is J5: `ADC2`, `AGND`, `ADC1`, `ADC0`, with a 0–3.3 V input limit. It is not the 60-pin cartridge interface and is not a fabrication release.

From the repository root, regenerate and validate it with:

```sh
/usr/bin/python3 hardware/kicad/bringup/generate_bringup.py
/usr/bin/python3 hardware/kicad/bringup/validate_bringup.py
```

The `bringup/README.md` records the verified Pico 2 physical numbering, candidate parts, provisional Gerber/Excellon outputs, and remaining electrical/mechanical review gates.

## Rev.A full live-cartridge functional circuit (draft)

The separate [`rev_a_logic/`](rev_a_logic/) project and [`rev-a-circuit-spec.md`](rev-a-circuit-spec.md) capture a full 60-pin functional circuit candidate. The intended partition uses independent 8-bit CPU/PPU data lanes, four 8-bit address latches with independent phase state, a 5-V CIRAM SRAM, cartridge IRQ/CIRAM feedback, and 3.3-V-only Pico-facing receive/status logic. GP26–GP28 are reserved for ADC0–ADC2, GP29 stays internal to Pico 2, and cartridge pin 31 remains explicitly unconnected.

The current native schematic is still a **functional candidate, not a fabrication schematic**. [`rev-a-circuit-spec.md`](rev-a-circuit-spec.md) now includes candidate DIP14 gate pin assignments for the 74AHCT00/04/08 control logic, but those gates are not yet instantiated as individual KiCad package units or checked against exact order codes. Power protection/current limit and audio conditioning remain abstract blocks. Pin 18 `CIRAM A10` is wired from the cartridge connector to SRAM A10, separate from PPU A10 on pin 53. `RUN_N AND PWR_GOOD` creates `BUS_RUN`, which disables buffers/latches and clears both phase flip-flops on reset or bad power. CPU/PPU address-load strobes now force their cart controls inactive and disable their borrowed data lanes; PPU status output is disabled during PPU read/write/address load. Connector fit, safe pulls, analog audio levels, rail sequencing and bus timing still need review and measurement.

Regenerate the functional schematic, export its netlist/PDF, and run both topology and Boolean checks from the repository root:

```sh
python3 hardware/kicad/rev_a_logic/generate_rev_a_schematic.py
kicad-cli sch export netlist --format kicadxml -o hardware/kicad/rev_a_logic/NESPICO_RevA.net.xml hardware/kicad/rev_a_logic/NESPICO_RevA.kicad_sch
kicad-cli sch export pdf -o hardware/kicad/rev_a_logic/NESPICO_RevA.pdf hardware/kicad/rev_a_logic/NESPICO_RevA.kicad_sch
python3 hardware/kicad/rev_a_logic/validate_rev_a_netlist.py
python3 hardware/kicad/validate_rev_a_logic.py
```

The last reviewed export had 133 nets/412 nodes; the stricter topology validator and 527 exhaustive Boolean assertions passed, including all GP0–GP22 logical connector pins and the address-strobe/status-MUX exclusion cases. KiCad 7.0.11 CLI in this environment exposes schematic export but not schematic ERC, so ERC is not claimed. These checks do not establish electrical margins, PIO setup/hold, chip timing, power sequencing or physical fit.

## Deliberate omissions / blockers before a board design

- The one-bit `NESPICO_Interface` slice does not assign Pico pins or physical footprints. The separate Rev.A functional candidate now proposes a logical GP0–GP22 assignment, but it is not a physical Pico 2 header map or a validated firmware contract.
- The earlier one-bit `NESPICO_Interface` experiment does not map the complete Famicom bus. The separate Rev.A functional candidate has a logical J5 60-pin signal map; connector mating, pin-31 variant behavior and electrical/timing validation remain open.
- The Rev.A candidate covers bus-wide functions and a logical 60-pin signal map, but control/power/audio are still functional blocks. Candidate discrete-gate pin allocations are documented but not instantiated/verified in KiCad; reset/pull defaults, cartridge 5-V protection, audio conditioning, ESD network, decoupling and exact package/footprint selection are not complete.
- Semiconductor packages/footprints and passive footprints are blank. Choose an exact orderable part/package and recheck the applicable full datasheet before layout.
- The separate OE nets must be driven with verified break-before-make timing. The related switch-level experiment and its limits are documented under [`../spice/`](../spice/README.md); its assumed cartridge disable delay is not a real-bus measurement.

The fitted 10 kΩ pull-ups and 100 nF bypasses are conventional placeholders for an early slice, not final values or a BOM recommendation. Do not connect this draft to a cartridge or fabricate it as-is.
