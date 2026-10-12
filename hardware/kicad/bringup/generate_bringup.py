#!/usr/bin/env python3
"""Generate the NESPICO Pico 2 8-bit electrical bring-up fixture (KiCad 7+).

This is a low-voltage measurement fixture, not a Famicom cartridge interface
or a fabrication release. GP26/27/28 are routed only to a 0-3.3 V ADC header;
GP29 is not a Pico 2 header pin and is not routed.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
PROJECT = "NESPICO_8bit_fixture"
LIBDIR = Path("/usr/share/kicad/symbols")
FPDIR = Path("/usr/share/kicad/footprints")
ROOT_UUID = str(uuid.uuid4())

FP_PICO = "Connector_PinSocket_2.54mm:PinSocket_1x20_P2.54mm_Vertical"
FP_BUS = "Connector_PinHeader_2.54mm:PinHeader_1x10_P2.54mm_Vertical"
FP_1X4 = "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"
FP_SOIC = "Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm"
FP_R = "Resistor_SMD:R_0805_2012Metric"
FP_C = "Capacitor_SMD:C_0805_2012Metric"

# Pin numbers are physical Pico 2 module header positions. GP26-28 are kept
# analog-only; GP29 is an internal VSYS-sense GPIO and has no header pad.
LEFT_PICO = {
    1: "CPU_D0", 2: "CPU_D1", 3: "GND", 4: "CPU_D2", 5: "CPU_D3",
    6: "CPU_D4", 7: "CPU_D5", 8: "GND", 9: "CPU_D6", 10: "CPU_D7",
    11: "PPU_D0", 12: "PPU_D1", 13: "GND", 14: "PPU_D2", 15: "PPU_D3",
    16: "PPU_D4", 17: "PPU_D5", 18: "GND", 19: "PPU_D6", 20: "PPU_D7",
}
RIGHT_PICO = {
    1: "+5V_USB", 2: None, 3: None, 4: None, 5: "+3V3",
    6: None, 7: "ADC2_IN", 8: "AGND", 9: "ADC1_IN", 10: "ADC0_IN",
    11: None, 12: None, 13: None, 14: None, 15: None, 16: None,
    17: None, 18: None, 19: "RX_OE_N", 20: "TX_OE_N",
}

NETS = [
    "GND", "AGND", "+3V3", "+5V_USB",
    *[f"CPU_D{i}" for i in range(8)],
    *[f"PPU_D{i}" for i in range(8)],
    *[f"TX_TEST_D{i}" for i in range(8)],
    *[f"RX_TEST_D{i}" for i in range(8)],
    "TX_OE_N", "RX_OE_N", "ADC0_IN", "ADC1_IN", "ADC2_IN",
]


def uid() -> str:
    return str(uuid.uuid4())


def q(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def num(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def extract_symbol(path: Path, name: str) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(rf'(?m)^  \(symbol "{re.escape(name)}"(?: |\))', text)
    if not m:
        raise RuntimeError(f"symbol {name!r} not found in {path}")
    start = m.start()
    depth = 0
    quoted = escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if quoted:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quoted = False
            continue
        if ch == '"':
            quoted = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise RuntimeError(f"unbalanced symbol {name!r}")


def symbol_pins(form: str) -> list[dict[str, object]]:
    result = []
    for m in re.finditer(r"(?m)^\s*\(pin\s", form):
        start, depth, quoted, escaped, end = m.start(), 0, False, False, None
        for i in range(start, len(form)):
            ch = form[i]
            if quoted:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    quoted = False
                continue
            if ch == '"':
                quoted = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            raise RuntimeError("unbalanced symbol pin")
        pin = form[start:end]
        at = re.search(r"\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\)", pin)
        number = re.search(r'\(number\s+"([^\"]+)"', pin)
        name = re.search(r'\(name\s+"([^\"]+)"', pin)
        if at and number and name:
            result.append({"x": float(at.group(1)), "y": float(at.group(2)),
                           "number": number.group(1), "name": name.group(1)})
    if not result:
        raise RuntimeError("symbol has no pins")
    return result


def qualify(form: str, library: str, name: str) -> str:
    return form.replace(f'(symbol "{name}"', f'(symbol "{library}:{name}"', 1)


def label(net: str, x: float, y: float, angle: int = 0) -> str:
    align = "right" if angle == 180 else "left"
    return f'''  (label {q(net)} (at {num(x)} {num(y)} {angle}) (fields_autoplaced)
    (effects (font (size 0.75 0.75)) (justify {align} bottom))
    (uuid {uid()})
  )'''


def nc(x: float, y: float) -> str:
    return f'  (no_connect (at {num(x)} {num(y)}) (uuid {uid()}))'


def text_block(text: str, x: float, y: float, size: float = 1.0) -> str:
    return f'''  (text {q(text)} (at {num(x)} {num(y)} 0)
    (effects (font (size {num(size)} {num(size)})) (justify left bottom))
    (uuid {uid()})
  )'''


def symbol_instance(lib_id: str, ref: str, value: str, footprint: str,
                    x: float, y: float, pins: list[dict[str, object]],
                    ref_xy: tuple[float, float], value_xy: tuple[float, float]) -> str:
    ins_uuid = uid()
    pin_uuids = "\n".join(
        f'    (pin {q(str(p["number"]))} (uuid {uid()}))' for p in pins
    )
    pin_instances = f'''    (instances
      (project {q(PROJECT)}
        (path "/{ROOT_UUID}" (reference {q(ref)}) (unit 1))
      )
    )'''
    return f'''  (symbol (lib_id {q(lib_id)}) (at {num(x)} {num(y)} 0) (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid {ins_uuid})
    (property "Reference" {q(ref)} (at {num(ref_xy[0])} {num(ref_xy[1])} 0)
      (effects (font (size 0.9 0.9)))
    )
    (property "Value" {q(value)} (at {num(value_xy[0])} {num(value_xy[1])} 0)
      (effects (font (size 0.85 0.85)))
    )
    (property "Footprint" {q(footprint)} (at {num(x)} {num(y)} 0)
      (effects (font (size 1 1)) hide)
    )
    (property "Datasheet" "" (at {num(x)} {num(y)} 0)
      (effects (font (size 1 1)) hide)
    )
{pin_uuids}
{pin_instances}
  )'''


def pin_position(x: float, y: float, pin: dict[str, object]) -> tuple[float, float]:
    return x + float(pin["x"]), y - float(pin["y"])


def make_schematic() -> None:
    symbols = [
        ("74xx", "74LS245", extract_symbol(LIBDIR / "74xx.kicad_sym", "74LS245")),
        ("Connector_Generic", "Conn_01x20", extract_symbol(LIBDIR / "Connector_Generic.kicad_sym", "Conn_01x20")),
        ("Connector_Generic", "Conn_01x10", extract_symbol(LIBDIR / "Connector_Generic.kicad_sym", "Conn_01x10")),
        ("Connector_Generic", "Conn_01x04", extract_symbol(LIBDIR / "Connector_Generic.kicad_sym", "Conn_01x04")),
        ("Device", "R", extract_symbol(LIBDIR / "Device.kicad_sym", "R")),
        ("Device", "C", extract_symbol(LIBDIR / "Device.kicad_sym", "C")),
    ]
    records = {(lib, name): symbol_pins(form) for lib, name, form in symbols}
    embedded = "\n".join(qualify(form, lib, name) for lib, name, form in symbols)
    positions = {
        "J1": (58.0, 100.0), "J2": (104.0, 100.0),
        "U1": (184.0, 87.0), "U2": (184.0, 180.0),
        "J3": (300.0, 82.0), "J4": (300.0, 180.0),
        "J5": (123.0, 232.0), "R1": (246.0, 51.0),
        "R2": (246.0, 148.0), "C1": (235.0, 86.0),
        "C2": (235.0, 181.0),
    }
    defs = [
        ("J1", "Connector_Generic", "Conn_01x20", "Pico 2 left socket", FP_PICO,
         {str(k): v for k, v in LEFT_PICO.items()}),
        ("J2", "Connector_Generic", "Conn_01x20", "Pico 2 right socket", FP_PICO,
         {str(k): v for k, v in RIGHT_PICO.items()}),
        ("U1", "74xx", "74LS245", "SN74AHCT245DW CPU TX", FP_SOIC,
         {"1": "+3V3", **{str(2+i): f"CPU_D{i}" for i in range(8)},
          "10": "GND", **{str(11+i): f"TX_TEST_D{7-i}" for i in range(8)},
          "19": "TX_OE_N", "20": "+5V_USB"}),
        ("U2", "74xx", "74LS245", "SN74LVC245ADW PPU RX", FP_SOIC,
         {"1": "GND", **{str(2+i): f"PPU_D{i}" for i in range(8)},
          "10": "GND", **{str(11+i): f"RX_TEST_D{7-i}" for i in range(8)},
          "19": "RX_OE_N", "20": "+3V3"}),
        ("J3", "Connector_Generic", "Conn_01x10", "CPU TX TEST ONLY", FP_BUS,
         {"1": "GND", **{str(2+i): f"TX_TEST_D{i}" for i in range(8)}, "10": "GND"}),
        ("J4", "Connector_Generic", "Conn_01x10", "PPU RX TEST INPUT", FP_BUS,
         {"1": "GND", **{str(2+i): f"RX_TEST_D{i}" for i in range(8)}, "10": "GND"}),
        ("J5", "Connector_Generic", "Conn_01x04", "ADC ONLY 0-3V3", FP_1X4,
         {"1": "ADC2_IN", "2": "AGND", "3": "ADC1_IN", "4": "ADC0_IN"}),
        ("R1", "Device", "R", "10k TX_OE_N pull-up", FP_R,
         {"1": "TX_OE_N", "2": "+3V3"}),
        ("R2", "Device", "R", "10k RX_OE_N pull-up", FP_R,
         {"1": "RX_OE_N", "2": "+3V3"}),
        ("C1", "Device", "C", "100n U1 bypass", FP_C,
         {"1": "+5V_USB", "2": "GND"}),
        ("C2", "Device", "C", "100n U2 bypass", FP_C,
         {"1": "+3V3", "2": "GND"}),
    ]
    values = {"J1": "Pico 2 L", "J2": "Pico 2 R", "U1": "SN74AHCT245DW",
              "U2": "SN74LVC245ADW", "J3": "CPU TX TEST ONLY",
              "J4": "PPU RX TEST INPUT", "J5": "ADC ONLY 0-3V3",
              "R1": "10k", "R2": "10k", "C1": "100n", "C2": "100n"}
    instances, labels, no_connects = [], [], []
    for ref, lib, name, _desc, footprint, pin_nets in defs:
        x, y = positions[ref]
        pins = records[(lib, name)]
        if ref in ("J1", "J2"):
            ref_xy, value_xy = (x + 9, y - 31), (x + 9, y + 31)
        elif ref in ("U1", "U2"):
            ref_xy, value_xy = (x, y - 22), (x, y + 25)
        else:
            ref_xy, value_xy = (x + 7, y - 4), (x + 7, y + 4)
        instances.append(symbol_instance(f"{lib}:{name}", ref, values[ref], footprint,
                                         x, y, pins, ref_xy, value_xy))
        for pin in pins:
            number = str(pin["number"])
            px, py = pin_position(x, y, pin)
            if number in pin_nets and pin_nets[number] is not None:
                angle = 180 if float(pin["x"]) < 0 else 0
                labels.append(label(str(pin_nets[number]), px, py, angle))
            else:
                no_connects.append(nc(px, py))

    notes = [
        text_block("NESPICO 8-BIT ELECTRICAL BRING-UP FIXTURE — DRAFT / NOT A CARTRIDGE INTERFACE", 28, 23, 1.35),
        text_block("J1 GP0-GP7 = CPU_D0-D7. U1 is fixed A->B, 3V3 Pico to 5V-side TX test header J3.", 28, 31, 0.9),
        text_block("J1 GP8-GP15 = PPU_D0-D7. U2 is fixed B->A, 5V-tolerant RX test header J4 to Pico.", 28, 38, 0.9),
        text_block("GP16 TX_OE_N; GP17 RX_OE_N. 10k pull-ups keep active-low OEs disabled at reset.", 28, 45, 0.9),
        text_block("J3 and J4 are separate, non-powered test ports; no cartridge connector or cartridge rail.", 28, 52, 0.9),
        text_block("GP26/27/28 only: ADC0/ADC1/ADC2 on J5 with AGND. Header input must stay within 0-3.3 V.", 28, 249, 0.9),
        text_block("Never drive ADC pins while Pico is unpowered. GP29 is internal VSYS sense; no external route.", 28, 256, 0.9),
        text_block("Prototype only. Review timing, protection, grounding, module fit and fabrication DRC before use.", 28, 263, 0.9),
    ]
    sch = f'''(kicad_sch (version 20230121) (generator "eeschema")
  (uuid {ROOT_UUID})
  (paper "A3")
  (title_block
    (title "NESPICO 8-bit bus bring-up fixture")
    (date "2026-10-12")
    (rev "DRAFT-1")
    (comment 1 "Independent CPU TX / PPU RX test lanes; not for cartridge or fabrication release")
  )
  (lib_symbols
{embedded}
  )
{chr(10).join(no_connects)}
{chr(10).join(labels)}
{chr(10).join(instances)}
{chr(10).join(notes)}
  (sheet_instances (path "/" (page "1")))
)
'''
    (HERE / f"{PROJECT}.kicad_sch").write_text(sch, encoding="utf-8")
    (HERE / f"{PROJECT}.kicad_pro").write_text("{}\n", encoding="utf-8")
    print(f"Generated schematic: {HERE / (PROJECT + '.kicad_sch')}")


def nm(value: float) -> int:
    return int(round(value * 1_000_000))


def vec(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(nm(x), nm(y))


def add_segment(board: pcbnew.BOARD, net, start: tuple[float, float],
                end: tuple[float, float], layer=pcbnew.F_Cu, width: float = 0.25) -> None:
    if start == end:
        return
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(vec(*start))
    track.SetEnd(vec(*end))
    track.SetWidth(nm(width))
    track.SetLayer(layer)
    track.SetNet(net)
    board.Add(track)


def add_route(board: pcbnew.BOARD, net, points: list[tuple[float, float]],
              layer=pcbnew.F_Cu, width: float = 0.25) -> None:
    for a, b in zip(points, points[1:]):
        add_segment(board, net, a, b, layer, width)


def add_via(board: pcbnew.BOARD, net, x: float, y: float,
            diameter: float = 0.6, drill: float = 0.3) -> None:
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(vec(x, y))
    via.SetWidth(nm(diameter))
    via.SetDrill(nm(drill))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNet(net)
    board.Add(via)


def add_edge(board: pcbnew.BOARD, a: tuple[float, float], b: tuple[float, float]) -> None:
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
    shape.SetStart(vec(*a))
    shape.SetEnd(vec(*b))
    shape.SetLayer(pcbnew.Edge_Cuts)
    shape.SetWidth(nm(0.05))
    board.Add(shape)


def add_text(board: pcbnew.BOARD, text: str, x: float, y: float,
             size: float = 1.0, thickness: float = 0.16,
             layer=pcbnew.F_SilkS) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(vec(x, y))
    item.SetLayer(layer)
    item.SetTextSize(vec(size, size))
    item.SetTextThickness(nm(thickness))
    board.Add(item)


def fp_pad(fp, number: int):
    for pad in fp.Pads():
        if pad.GetNumber() == str(number):
            return pad
    raise RuntimeError(f"pad {number} not found on {fp.GetReference()}")


def pad_xy(fp, number: int) -> tuple[float, float]:
    p = fp_pad(fp, number).GetPosition()
    return pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)


def make_board() -> None:
    board = pcbnew.BOARD()
    if hasattr(board.GetDesignSettings(), "SetCopperLayerCount"):
        board.GetDesignSettings().SetCopperLayerCount(2)
    board.GetDesignSettings().SetBoardThickness(nm(1.6))
    board.SetTitleBlock(pcbnew.TITLE_BLOCK())
    board.GetTitleBlock().SetTitle("NESPICO 8-bit bus bring-up fixture")
    board.GetTitleBlock().SetRevision("DRAFT-1 — NOT FOR FAB")

    net_info = {}
    for name in NETS:
        item = pcbnew.NETINFO_ITEM(board, name)
        board.Add(item)
        net_info[name] = item

    footprint_specs = [
        ("J1", "Pico 2 left socket", FP_PICO, (12.0, 10.0), 0),
        ("J2", "Pico 2 right socket", FP_PICO, (29.78, 10.0), 0),
        ("U1", "SN74AHCT245DW CPU TX", FP_SOIC, (51.0, 27.0), 0),
        ("U2", "SN74LVC245ADW PPU RX", FP_SOIC, (51.0, 52.0), 0),
        ("J3", "CPU TX TEST ONLY - 5V SIDE", FP_BUS, (94.0, 20.0), 0),
        ("J4", "PPU RX TEST INPUT - 5V TOLERANT", FP_BUS, (94.0, 47.0), 0),
        ("J5", "ADC ONLY 0-3V3", FP_1X4, (40.0, 3.0), 0),
        ("R1", "10k TX_OE_N pull-up", FP_R, (63.0, 15.0), 0),
        ("R2", "10k RX_OE_N pull-up", FP_R, (63.0, 40.0), 0),
        ("C1", "100n U1 bypass", FP_C, (57.0, 17.0), 0),
        ("C2", "100n U2 bypass", FP_C, (72.0, 43.0), 0),
    ]
    padnets = {
        "J1": {str(k): v for k, v in LEFT_PICO.items()},
        "J2": {str(k): v for k, v in RIGHT_PICO.items()},
        "U1": {"1": "+3V3", **{str(2+i): f"CPU_D{i}" for i in range(8)},
               "10": "GND", **{str(11+i): f"TX_TEST_D{7-i}" for i in range(8)},
               "19": "TX_OE_N", "20": "+5V_USB"},
        "U2": {"1": "GND", **{str(2+i): f"PPU_D{i}" for i in range(8)},
               "10": "GND", **{str(11+i): f"RX_TEST_D{7-i}" for i in range(8)},
               "19": "RX_OE_N", "20": "+3V3"},
        "J3": {"1": "GND", **{str(2+i): f"TX_TEST_D{i}" for i in range(8)}, "10": "GND"},
        "J4": {"1": "GND", **{str(2+i): f"RX_TEST_D{i}" for i in range(8)}, "10": "GND"},
        "J5": {"1": "ADC2_IN", "2": "AGND", "3": "ADC1_IN", "4": "ADC0_IN"},
        "R1": {"1": "TX_OE_N", "2": "+3V3"},
        "R2": {"1": "RX_OE_N", "2": "+3V3"},
        "C1": {"1": "+5V_USB", "2": "GND"},
        "C2": {"1": "+3V3", "2": "GND"},
    }
    footprints = {}
    for ref, value, fpid, position, rotation in footprint_specs:
        lib, footprint_name = fpid.split(":", 1)
        fp = pcbnew.FootprintLoad(str(FPDIR / f"{lib}.pretty"), footprint_name)
        if fp is None:
            raise RuntimeError(f"unable to load footprint {fpid}")
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPosition(vec(*position))
        fp.SetOrientationDegrees(rotation)
        if ref == "J5":
            fp.Reference().SetPosition(vec(42.0, 1.25))
            fp.Reference().SetTextSize(vec(0.7, 0.7))
        board.Add(fp)
        footprints[ref] = fp
        for pad in fp.Pads():
            name = padnets[ref].get(pad.GetNumber())
            if name:
                pad.SetNet(net_info[name])

    # Outline: 100 x 82 mm, 2-layer FR-4. This is a placement/routing draft.
    add_edge(board, (0, 0), (100, 0))
    add_edge(board, (100, 0), (100, 82))
    add_edge(board, (100, 82), (0, 82))
    add_edge(board, (0, 82), (0, 0))

    # Pico GP0-7 -> CPU transmit lane (U1 A0-7), then 5 V-side J3.
    cpu_pico_pads = [1, 2, 4, 5, 6, 7, 9, 10]
    for i, pico_pad in enumerate(cpu_pico_pads):
        net = net_info[f"CPU_D{i}"]
        # The CPU lane passes between the two Pico socket rows through the
        # center of successive 2.54 mm gaps; 0.15 mm tracks preserve clearance.
        slot_y = 16.35 + 2.54 * i
        add_route(board, net, [pad_xy(footprints["J1"], pico_pad), (29.78, slot_y),
                               pad_xy(footprints["U1"], 2 + i)], pcbnew.F_Cu, 0.15)
        add_route(board, net, [pad_xy(footprints["U1"], 18 - i),
                               pad_xy(footprints["J3"], 2 + i)], pcbnew.F_Cu, 0.25)

    # Pico GP8-15 <- PPU receive lane (U2 A0-7) <- separate 5 V-tolerant J4.
    ppu_pico_pads = [11, 12, 14, 15, 16, 17, 19, 20]
    for i, pico_pad in enumerate(ppu_pico_pads):
        net = net_info[f"PPU_D{i}"]
        add_route(board, net, [pad_xy(footprints["J4"], 2 + i),
                               pad_xy(footprints["U2"], 18 - i)], pcbnew.F_Cu, 0.25)
        # The PPU lane also crosses the right socket row only through pin gaps.
        slot_y = 39.21 + 2.54 * i
        add_route(board, net, [pad_xy(footprints["U2"], 2 + i), (29.78, slot_y),
                               pad_xy(footprints["J1"], pico_pad)], pcbnew.F_Cu, 0.15)

    # ADC breakout is routed on B.Cu to keep the analog input traces separated
    # from the fast digital fan-outs. Physical header order: ADC2, AGND, ADC1, ADC0.
    for header_pin, pico_pad, name in [(1, 7, "ADC2_IN"), (2, 8, "AGND"),
                                       (3, 9, "ADC1_IN"), (4, 10, "ADC0_IN")]:
        i = header_pin - 1
        pico_xy = pad_xy(footprints["J2"], pico_pad)
        escape_x = 33.0 + 1.8 * i
        header_xy = pad_xy(footprints["J5"], header_pin)
        add_route(board, net_info[name],
                  [pico_xy, (escape_x, pico_xy[1]), (escape_x, header_xy[1]), header_xy],
                  pcbnew.B_Cu, 0.25)

    # OEs are active low, pulled up to 3V3 and controlled by GP16/GP17.
    txvia, rxvia = (57.5, 22.555), (57.5, 47.555)
    add_via(board, net_info["TX_OE_N"], *txvia)
    add_via(board, net_info["RX_OE_N"], *rxvia)
    txsrc = pad_xy(footprints["J2"], 20)
    # Go right, then up at x=59: this avoids RX_OE_N and the adjacent +3V3 rail.
    add_route(board, net_info["TX_OE_N"],
              [txsrc, (59.0, txsrc[1]), (59.0, txvia[1]), txvia], pcbnew.B_Cu, 0.25)
    add_route(board, net_info["RX_OE_N"],
              [pad_xy(footprints["J2"], 19), rxvia], pcbnew.B_Cu, 0.25)
    add_route(board, net_info["TX_OE_N"],
              [txvia, pad_xy(footprints["U1"], 19)], pcbnew.F_Cu, 0.25)
    add_route(board, net_info["RX_OE_N"],
              [rxvia, pad_xy(footprints["U2"], 19)], pcbnew.F_Cu, 0.25)
    # Pull-up escape routing clears the adjacent SOIC VCC/data pads.
    add_route(board, net_info["TX_OE_N"],
              [pad_xy(footprints["U1"], 19), (63.0, 22.555), (63.0, 15.0),
               pad_xy(footprints["R1"], 1)], pcbnew.F_Cu, 0.25)
    add_route(board, net_info["RX_OE_N"],
              [pad_xy(footprints["U2"], 19), (63.0, 47.555), (63.0, 40.0),
               pad_xy(footprints["R2"], 1)], pcbnew.F_Cu, 0.25)

    # VBUS powers U1 only. It is not a cartridge power output.
    add_route(board, net_info["+5V_USB"],
              [pad_xy(footprints["J2"], 1), pad_xy(footprints["U1"], 20)],
              pcbnew.F_Cu, 0.4)
    add_route(board, net_info["+5V_USB"],
              [pad_xy(footprints["U1"], 20), pad_xy(footprints["C1"], 1)],
              pcbnew.F_Cu, 0.3)

    # 3V3 backbone on B.Cu supplies U2, AHCT DIR, and both OE pull-ups.
    # 3.3 V satisfies the SN74AHCT245 VIH requirement at 5 V VCC.
    p3v3 = pad_xy(footprints["J2"], 5)
    p3v3_escape = (31.3, 6.0)
    vtop, vcc_rx, vpull_rx, vdir = (60.0, 6.0), (60.0, 46.0), (67.0, 40.0), (46.35, 18.0)
    for pt in (p3v3_escape, vtop, vcc_rx, vpull_rx, vdir):
        add_via(board, net_info["+3V3"], *pt)
    add_route(board, net_info["+3V3"], [p3v3, (31.3, p3v3[1]), p3v3_escape], pcbnew.B_Cu, 0.35)
    add_route(board, net_info["+3V3"], [p3v3_escape, (37.0, 6.0), (37.0, 12.2),
                                       (45.0, 12.2), vtop], pcbnew.F_Cu, 0.35)
    add_route(board, net_info["+3V3"], [vtop, vcc_rx], pcbnew.B_Cu, 0.35)
    add_route(board, net_info["+3V3"], [vtop, (46.35, 10.0), vdir], pcbnew.B_Cu, 0.3)
    add_route(board, net_info["+3V3"], [vtop, (67.0, 10.0), vpull_rx], pcbnew.B_Cu, 0.3)
    add_route(board, net_info["+3V3"],
              [pad_xy(footprints["U1"], 1), vdir], pcbnew.F_Cu, 0.25)
    add_route(board, net_info["+3V3"],
              [vcc_rx, pad_xy(footprints["U2"], 20)], pcbnew.F_Cu, 0.25)
    add_route(board, net_info["+3V3"],
              [pad_xy(footprints["R1"], 2), vtop], pcbnew.F_Cu, 0.25)
    add_route(board, net_info["+3V3"],
              [pad_xy(footprints["R2"], 2), vpull_rx], pcbnew.F_Cu, 0.25)
    add_route(board, net_info["+3V3"],
              [vpull_rx, pad_xy(footprints["C2"], 1)], pcbnew.F_Cu, 0.3)

    # Explicit GND routing; no unfilled copper zone is assumed.
    gnd = net_info["GND"]
    ground_vias = [
        ("U1", 10, (51.0, 34.0)),
        ("U2", 10, (46.35, 60.0)),
        ("U2", 1, (44.0, 44.0)),
        ("C1", 2, (58.0, 18.5)),
        ("C2", 2, (74.0, 44.5)),
    ]
    for ref, pin, via_at in ground_vias:
        vx, vy = via_at
        add_via(board, gnd, vx, vy)
        add_route(board, gnd, [pad_xy(footprints[ref], pin), via_at], pcbnew.F_Cu, 0.25)
    ground_rows = [15.08, 27.78, 40.48, 53.18]
    add_route(board, gnd, [(8.0, ground_rows[0]), (8.0, ground_rows[-1])], pcbnew.B_Cu, 0.6)
    for gy in ground_rows:
        add_route(board, gnd, [(8.0, gy), (12.0, gy)], pcbnew.B_Cu, 0.6)
    add_route(board, gnd, [(8.0, 53.18), (8.0, 77.0), (98.0, 77.0), (98.0, 17.0)], pcbnew.B_Cu, 0.6)
    # Route chip grounds around the Pico rows and above the ADC fan-out.
    add_route(board, gnd, [(51.0, 34.0), (44.0, 34.0), (44.0, 1.0),
                           (8.0, 1.0), (8.0, 15.08)], pcbnew.B_Cu, 0.6)
    add_route(board, gnd, [(44.0, 44.0), (44.0, 34.0)], pcbnew.B_Cu, 0.6)
    add_route(board, gnd, [(46.35, 60.0), (46.35, 64.0), (8.0, 64.0),
                           (8.0, 60.0)], pcbnew.B_Cu, 0.6)
    # C1 joins U1 ground on the component side of the Pico sockets; C2 joins
    # the right-side return without crossing the +3V3 trunk.
    add_route(board, gnd, [(58.0, 18.5), (56.0, 18.5), (51.0, 34.0)], pcbnew.B_Cu, 0.6)
    add_route(board, gnd, [(74.0, 44.5), (98.0, 44.5)], pcbnew.B_Cu, 0.6)
    for ref, pin in [("J3", 1), ("J3", 10), ("J4", 1), ("J4", 10)]:
        start = pad_xy(footprints[ref], pin)
        add_route(board, gnd, [start, (98.0, start[1])], pcbnew.B_Cu, 0.6)

    # Silkscreen calls out direction, voltage boundary, ADC pin order, and the
    # fact that these headers must not be plugged into a cartridge.
    add_text(board, "NESPICO 8-BIT BRING-UP", 72.0, 5.0, 1.1)
    add_text(board, "DRAFT - TEST ONLY - NO CART", 34.0, 79.5, 1.25)
    add_text(board, "J3 CPU TX / 5V SIDE", 82.0, 16.2, 0.8)
    add_text(board, "J4 PPU RX / 5V-TOL INPUT", 76.0, 43.3, 0.8)
    for i, name in enumerate(("1 ADC2", "2 AGND", "3 ADC1", "4 ADC0")):
        add_text(board, name, 42.0, 3.0 + 2.54 * i, 0.6, 0.12)
    add_text(board, "ADC 0-3.3V MAX", 69.0, 12.0, 0.7, 0.14)
    add_text(board, "GP16 TX_OE_N / GP17 RX_OE_N", 35.0, 64.0, 0.75)
    add_text(board, "GP26-28 ADC ONLY; GP29 INTERNAL", 34.0, 67.0, 0.75)

    pcb_path = HERE / f"{PROJECT}.kicad_pcb"
    pcbnew.SaveBoard(str(pcb_path), board)
    print(f"Generated board: {pcb_path}")
    print(f"  footprints={len(footprints)} nets={len(NETS)} tracks={len(board.GetTracks())}")


def main() -> int:
    if not (LIBDIR / "74xx.kicad_sym").exists():
        raise SystemExit("KiCad standard symbol library not found under /usr/share/kicad/symbols")
    make_schematic()
    make_board()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
