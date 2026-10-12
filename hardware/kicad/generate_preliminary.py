#!/usr/bin/env python3
"""Generate a preliminary one-bit NESPICO bus-interface KiCad schematic.

The pin geometry is copied from the installed KiCad 7 74HC244 / Device:R,C
symbols. The two 244 candidates share that standard pinout. No footprints or
board-specific GPIO assignments are selected.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = Path("/usr/share/kicad/symbols")
LIB_NAME = "NESPICO_Interface"
PROJECT = "NESPICO_Interface"
ROOT_UUID = str(uuid.uuid4())


def uid() -> str:
    return str(uuid.uuid4())


def extract_top_symbol(path: Path, name: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf'(?m)^  \(symbol "{re.escape(name)}"(?: |\))', text)
    if not match:
        raise RuntimeError(f"symbol {name!r} not found in {path}")
    start = match.start()
    depth = 0
    quoted = False
    escaped = False
    for pos in range(start, len(text)):
        char = text[pos]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start : pos + 1]
    raise RuntimeError(f"unbalanced symbol form for {name!r}")


def pin_records(symbol_form: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for match in re.finditer(r"(?m)^\s*\(pin\s", symbol_form):
        start = match.start()
        depth = 0
        quoted = False
        escaped = False
        end = None
        for pos in range(start, len(symbol_form)):
            char = symbol_form[pos]
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
                continue
            if char == '"':
                quoted = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    end = pos + 1
                    break
        if end is None:
            raise RuntimeError("unbalanced pin definition")
        pin = symbol_form[start:end]
        pos = re.search(r"\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\)", pin)
        number = re.search(r'\(number\s+"([^\"]+)"', pin)
        name = re.search(r'\(name\s+"([^\"]+)"', pin)
        if pos and number and name:
            records.append({
                "x": float(pos.group(1)),
                "y": float(pos.group(2)),
                "number": number.group(1),
                "name": name.group(1),
            })
    if not records:
        raise RuntimeError("no pins extracted from symbol")
    return records


def clone_244(name: str, datasheet: str) -> str:
    form = extract_top_symbol(LIB / "74xx.kicad_sym", "74HC244")
    form = form.replace("74HC244", name)
    form = form.replace(
        "https://assets.nexperia.com/documents/data-sheet/74HC_HCT244.pdf",
        datasheet,
    )
    if f'(symbol "{name}"' not in form:
        raise RuntimeError(f"failed to rename 244 symbol to {name}")
    return form


def qualified_form(form: str, local_name: str) -> str:
    return form.replace(f'(symbol "{local_name}"', f'(symbol "{LIB_NAME}:{local_name}"', 1)


def q(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def n(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def label(name: str, x: float, y: float, angle: int = 0) -> str:
    align = "right" if angle == 180 else "left"
    return f'''  (label {q(name)} (at {n(x)} {n(y)} {angle}) (fields_autoplaced)
    (effects (font (size 1.0 1.0)) (justify {align} bottom))
    (uuid {uid()})
  )'''


def wire(x1: float, y1: float, x2: float, y2: float) -> str:
    return f'''  (wire (pts (xy {n(x1)} {n(y1)}) (xy {n(x2)} {n(y2)}))
    (stroke (width 0) (type solid))
    (uuid {uid()})
  )'''


def no_connect(x: float, y: float) -> str:
    return f'  (no_connect (at {n(x)} {n(y)}) (uuid {uid()}))'


def text_block(text: str, x: float, y: float, size: float = 1.1) -> str:
    return f'''  (text {q(text)} (at {n(x)} {n(y)} 0)
    (effects (font (size {n(size)} {n(size)})) (justify left bottom))
    (uuid {uid()})
  )'''


def instance(
    lib_id: str,
    reference: str,
    value: str,
    x: float,
    y: float,
    pins: list[dict[str, object]],
    datasheet: str = "",
    ref_y: float | None = None,
    value_y: float | None = None,
) -> str:
    ref_y = y - 23 if ref_y is None else ref_y
    value_y = y + 22 if value_y is None else value_y
    instance_uuid = uid()
    pin_text = "\n".join(
        f'    (pin {q(str(pin["number"]))} (uuid {uid()}))' for pin in pins
    )
    footprint = ""
    return f'''  (symbol (lib_id {q(lib_id)}) (at {n(x)} {n(y)} 0) (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid {instance_uuid})
    (property "Reference" {q(reference)} (at {n(x)} {n(ref_y)} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" {q(value)} (at {n(x)} {n(value_y)} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Footprint" {q(footprint)} (at {n(x)} {n(y)} 0)
      (effects (font (size 1.0 1.0)) hide)
    )
    (property "Datasheet" {q(datasheet)} (at {n(x)} {n(y)} 0)
      (effects (font (size 1.0 1.0)) hide)
    )
{pin_text}
    (instances
      (project {q(PROJECT)}
        (path "/{ROOT_UUID}" (reference {q(reference)}) (unit 1))
      )
    )
  )'''


def label_pin(pin: dict[str, object], cx: float, cy: float, net: str, *, angle: int | None = None) -> str:
    px = cx + float(pin["x"])
    py = cy - float(pin["y"])
    if angle is None:
        angle = 180 if float(pin["x"]) < 0 else 0
    return label(net, px, py, angle)


def make_chip_wiring(
    pins: list[dict[str, object]],
    cx: float,
    cy: float,
    *,
    data_in: str,
    data_out: str,
    oe: str,
    vcc: str,
) -> tuple[list[str], list[str]]:
    labels: list[str] = []
    nc: list[str] = []
    for pin in pins:
        name = str(pin["name"])
        px = cx + float(pin["x"])
        py = cy - float(pin["y"])
        if name == "1A0":
            labels.append(label_pin(pin, cx, cy, data_in))
        elif name == "1Y0":
            if data_out == "CART_D0":
                # Connected to the receive-buffer input by a drawn wire below.
                pass
            else:
                labels.append(label_pin(pin, cx, cy, data_out))
        elif name == "1OE":
            labels.append(label_pin(pin, cx, cy, oe))
        elif name == "2OE":
            labels.append(label_pin(pin, cx, cy, "+3V3_LOGIC"))
        elif name == "VCC":
            labels.append(label_pin(pin, cx, cy, vcc))
        elif name == "GND":
            labels.append(label_pin(pin, cx, cy, "GND"))
        elif name.endswith("A0") or name.endswith("A1") or name.endswith("A2") or name.endswith("A3"):
            labels.append(label_pin(pin, cx, cy, "GND"))
        elif name.endswith("Y0") or name.endswith("Y1") or name.endswith("Y2") or name.endswith("Y3"):
            nc.append(no_connect(px, py))
        else:
            raise RuntimeError(f"unexpected 244 pin name {name!r}")
    return labels, nc


def resistor_instance(reference: str, value: str, x: float, y: float, pin_data: list[dict[str, object]]) -> str:
    return instance(f"{LIB_NAME}:R", reference, value, x, y, pin_data, ref_y=y-7, value_y=y)


def capacitor_instance(reference: str, value: str, x: float, y: float, pin_data: list[dict[str, object]]) -> str:
    return instance(f"{LIB_NAME}:C", reference, value, x, y, pin_data, ref_y=y-7, value_y=y+6)


def main() -> None:
    ahct = clone_244("SN74AHCT244", "https://www.ti.com/lit/ds/scls228m/scls228m.pdf")
    lvc = clone_244("SN74LVC244A", "https://www.ti.com/lit/ds/symlink/sn74lvc244a.pdf")
    resistor = extract_top_symbol(LIB / "Device.kicad_sym", "R")
    capacitor = extract_top_symbol(LIB / "Device.kicad_sym", "C")
    symbol_forms = {
        "SN74AHCT244": ahct,
        "SN74LVC244A": lvc,
        "R": resistor,
        "C": capacitor,
    }
    records = {name: pin_records(form) for name, form in symbol_forms.items()}

    lib = "(kicad_symbol_lib (version 20220914) (generator \"kicad_symbol_editor\")\n"
    lib += "\n".join(symbol_forms.values()) + "\n)\n"
    (HERE / f"{LIB_NAME}.kicad_sym").write_text(lib, encoding="utf-8")

    embedded = "\n".join(
        qualified_form(form, name) for name, form in symbol_forms.items()
    )
    elements: list[str] = []
    no_connects: list[str] = []

    # U1: MCU-to-cartridge 3.3-V logic -> 5-V AHCT transmit path.
    u1x, u1y = 100.0, 100.0
    u1 = records["SN74AHCT244"]
    u1_labels, u1_nc = make_chip_wiring(
        u1, u1x, u1y, data_in="MCU_D0", data_out="CART_D0", oe="TX_OE_N", vcc="+5V_BUFFER"
    )
    elements.extend(u1_labels)
    no_connects.extend(u1_nc)
    elements.append(instance(
        f"{LIB_NAME}:SN74AHCT244", "U1", "SN74AHCT244", u1x, u1y, u1,
        "https://www.ti.com/lit/ds/scls228m/scls228m.pdf", ref_y=74, value_y=126,
    ))

    # U2: cartridge 5-V receive -> 3.3-V MCU data input.
    u2x, u2y = 200.0, 100.0
    u2 = records["SN74LVC244A"]
    u2_labels, u2_nc = make_chip_wiring(
        u2, u2x, u2y, data_in="CART_D0", data_out="MCU_D0", oe="RX_OE_N", vcc="+3V3_LOGIC"
    )
    elements.extend(u2_labels)
    no_connects.extend(u2_nc)
    elements.append(instance(
        f"{LIB_NAME}:SN74LVC244A", "U2", "SN74LVC244A", u2x, u2y, u2,
        "https://www.ti.com/lit/ds/symlink/sn74lvc244a.pdf", ref_y=74, value_y=126,
    ))

    # One named cartridge-side D0 bus between the two one-bit paths.
    u1_y0 = next(p for p in u1 if p["name"] == "1Y0")
    u2_a0 = next(p for p in u2 if p["name"] == "1A0")
    x1, y1 = u1x + float(u1_y0["x"]), u1y - float(u1_y0["y"])
    x2, y2 = u2x + float(u2_a0["x"]), u2y - float(u2_a0["y"])
    if abs(y1 - y2) > 1e-6 or x2 <= x1:
        raise RuntimeError("244 symbols do not align for the cartridge data net")
    elements.append(wire(x1, y1, x2, y2))
    elements.append(label("CART_D0", (x1 + x2) / 2, y1, 0))

    # Safe default pull-ups: both active-low enables deasserted while MCU is reset.
    r_pins = records["R"]
    for reference, net, x in (("R1", "TX_OE_N", 42.0), ("R2", "RX_OE_N", 62.0)):
        ry = 150.0
        elements.append(resistor_instance(reference, "10k", x, ry, r_pins))
        # Standard Device:R pin 1 is +3.81 local y; pin 2 is -3.81 local y.
        elements.append(label(net, x, ry - 3.81, 0))
        elements.append(label("+3V3_LOGIC", x, ry + 3.81, 0))

    # Local decoupling placeholders; package/placement still TBD.
    c_pins = records["C"]
    for reference, rail, x in (("C1", "+5V_BUFFER", 145.0), ("C2", "+3V3_LOGIC", 245.0)):
        cy = 150.0
        elements.append(capacitor_instance(reference, "100n", x, cy, c_pins))
        elements.append(label(rail, x, cy - 3.81, 0))
        elements.append(label("GND", x, cy + 3.81, 0))

    elements.extend([
        text_block("PRELIMINARY ONE-BIT SLICE — NOT FOR FABRICATION", 35, 28, 1.5),
        text_block("D0 is generic; no Famicom connector pin or RP2350 GPIO number assigned.", 35, 36),
        text_block("U1 TX and U2 RX enables must be mutually exclusive; dead time requires actual hardware validation.", 35, 43),
        text_block("Unused 244 inputs are tied low; unused outputs are no-connect; second OE groups stay disabled.", 35, 50),
        text_block("+5V_BUFFER and +3V3_LOGIC are external logic rails; source, protection, and sequencing are not designed.", 35, 57),
        text_block("Footprints, bypass placement, all other bus bits, and cartridge connector are deliberately unassigned.", 35, 64),
    ])

    title = "NESPICO — preliminary one-bit bus turnaround slice"
    sch = f'''(kicad_sch (version 20230121) (generator "eeschema")
  (uuid {ROOT_UUID})
  (paper "A4")
  (title_block
    (title {q(title)})
    (date "2026-10-12")
    (rev "DRAFT-0")
    (comment 1 "Candidate level-interface only; not a complete schematic")
  )
  (lib_symbols
{embedded}
  )
{chr(10).join(no_connects)}
{chr(10).join(elements)}
  (sheet_instances (path "/" (page "1")))
)
'''
    (HERE / f"{PROJECT}.kicad_sch").write_text(sch, encoding="utf-8")

    lib_table = f'''(sym_lib_table
  (version 7)
  (lib (name "{LIB_NAME}") (type "KiCad") (uri "${{KIPRJMOD}}/{LIB_NAME}.kicad_sym") (options "") (descr "Preliminary NESPICO interface symbols"))
)
'''
    (HERE / "sym-lib-table").write_text(lib_table, encoding="utf-8")
    # The matching project file makes the adjacent project-local sym-lib-table
    # available when opening the project in KiCad. Empty JSON uses KiCad defaults.
    (HERE / f"{PROJECT}.kicad_pro").write_text("{}\n", encoding="utf-8")
    print(f"Generated {HERE / (PROJECT + '.kicad_sch')}")
    print(f"Generated {HERE / (LIB_NAME + '.kicad_sym')}")
    print(f"Generated {HERE / 'sym-lib-table'}")
    print(f"Generated {HERE / (PROJECT + '.kicad_pro')}")


if __name__ == "__main__":
    main()
