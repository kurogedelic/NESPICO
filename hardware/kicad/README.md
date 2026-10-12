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

From the repository root:

```sh
python3 hardware/kicad/generate_preliminary.py
python3 hardware/kicad/validate_preliminary.py
kicad-cli sch export pdf hardware/kicad/NESPICO_Interface.kicad_sch -o hardware/kicad/NESPICO_Interface.pdf
```

The generation script expects a KiCad installation whose standard symbol files live under `/usr/share/kicad/symbols`; the checked-in schematic and local library are ordinary KiCad files and remain available independently of rerunning the generator.

## Deliberate omissions / blockers before a board design

- No actual YD-RP2350A Zero GPIO pin selection, module footprint, or routing is assigned; the module's physical pinout has not been verified.
- `MCU_D0` and `CART_D0` are functional net names only. The Famicom connector pin is deliberately not assigned because this sheet does not yet distinguish every bus timing/use case.
- No complete bus-wide design, address/control signals, reset, connector, protection, cartridge 5-V source, 3.3-V regulator, power sequencing, ESD network, or decoupling placement is included.
- Semiconductor packages/footprints and passive footprints are blank. Choose an exact orderable part/package and recheck the applicable full datasheet before layout.
- The separate OE nets must be driven with verified break-before-make timing. The related switch-level experiment and its limits are documented under [`../spice/`](../spice/README.md); its assumed cartridge disable delay is not a real-bus measurement.

The fitted 10 kΩ pull-ups and 100 nF bypasses are conventional placeholders for an early slice, not final values or a BOM recommendation. Do not connect this draft to a cartridge or fabricate it as-is.
