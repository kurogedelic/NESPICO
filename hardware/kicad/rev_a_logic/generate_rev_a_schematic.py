#!/usr/bin/env python3
"""Generate a functional-level KiCad schematic for the NESPICO Rev.A candidate.

The file is deliberately not a fabrication schematic: connector footprints,
protection, exact orderable packages, audio analog values, and cartridge power
parts remain open. Physical package symbols are used for buffers, latches, SRAM
and multiplexers; logic/power/audio abstractions are explicitly marked as blocks.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LIB_DIR = Path("/usr/share/kicad/symbols")
LIB_NAME = "NESPICO_RevA"
PROJECT = "NESPICO_RevA"
ROOT_UUID = str(uuid.uuid4())

spec = importlib.util.spec_from_file_location("preliminary_helpers", ROOT / "generate_preliminary.py")
assert spec and spec.loader
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)
base.LIB_NAME = LIB_NAME
base.PROJECT = PROJECT
base.ROOT_UUID = ROOT_UUID


def custom_symbol(name: str, pins: list[tuple[str, str, str, str]], *, datasheet: str = "", bom: bool = True,
                  hide_pin_names: bool = False) -> str:
    """One-unit rectangular symbol. Pin entries are (number, name, side, type)."""
    left = [p for p in pins if p[2] == "left"]
    right = [p for p in pins if p[2] == "right"]
    count = max(len(left), len(right), 2)
    step = 2.54
    body_h = count * step + 2.54
    top = (count - 1) * step / 2
    symbol_h = body_h / 2
    q = base.q
    n = base.n
    bom_text = "yes" if bom else "no"
    inner: list[str] = []
    for side, group in (("left", left), ("right", right)):
        for i, (number, pname, _, pin_type) in enumerate(group):
            y = top - i * step
            x = -12.7 if side == "left" else 12.7
            angle = 0 if side == "left" else 180
            visible_name = "~" if hide_pin_names else pname
            inner.append(
                f'''    (pin {pin_type} line (at {n(x)} {n(y)} {angle}) (length 5.08)
      (name {q(visible_name)} (effects (font (size 1.0 1.0))))
      (number {q(number)} (effects (font (size 1.0 1.0))))
    )'''
            )
    return f'''(symbol {q(name)}
  (pin_names (offset 0.508))
  (in_bom {bom_text}) (on_board {bom_text})
  (property "Reference" "U" (at 0 {n(symbol_h + 3.81)} 0)
    (effects (font (size 1.27 1.27))))
  (property "Value" {q(name)} (at 0 {n(-symbol_h - 3.81)} 0)
    (effects (font (size 1.27 1.27))))
  (property "Footprint" "" (at 0 0 0) (effects (font (size 1 1)) hide))
  (property "Datasheet" {q(datasheet)} (at 0 0 0) (effects (font (size 1 1)) hide))
  (symbol {q(name + "_0_1")}
    (rectangle (start -7.62 {n(symbol_h)}) (end 7.62 {n(-symbol_h)})
      (stroke (width 0.254) (type default)) (fill (type background)))
  )
  (symbol {q(name + "_1_1")}
{chr(10).join(inner)}
  )
)'''


def custom_pin_records(form: str) -> list[dict[str, object]]:
    return base.pin_records(form)


def clone_symbol(libfile: str, source: str, target: str, datasheet: str = "", replacements: dict[str, str] | None = None) -> str:
    form = base.extract_top_symbol(LIB_DIR / libfile, source)
    form = form.replace(source, target)
    if replacements:
        for old, new in replacements.items():
            form = form.replace(old, new)
    if datasheet:
        form = re.sub(r'\(property "Datasheet" "[^\"]*"', f'(property "Datasheet" {base.q(datasheet)}', form)
    return form


def make_instance(lib_id: str, ref: str, value: str, x: float, y: float,
                  pins: list[dict[str, object]], *, datasheet: str = "",
                  ref_y: float | None = None, value_y: float | None = None,
                  abstract: bool = False) -> str:
    out = base.instance(lib_id, ref, value, x, y, pins, datasheet,
                        ref_y=ref_y, value_y=value_y)
    if abstract:
        out = out.replace('(in_bom yes) (on_board yes) (dnp no)',
                          '(in_bom no) (on_board no) (dnp no)')
    return out


def attach_all(ref: str, form: str, x: float, y: float, nets: dict[str, str], *, nc: set[str] | None = None) -> list[str]:
    pins = custom_pin_records(form)
    by_number = {str(p["number"]): p for p in pins}
    if len(by_number) != len(pins):
        raise ValueError(f"duplicate pin number in {ref}")
    lines: list[str] = []
    nc = nc or set()
    for number, pin in by_number.items():
        name = str(pin["name"])
        px = x + float(pin["x"])
        py = y - float(pin["y"])
        if number in nc:
            lines.append(base.no_connect(px, py))
        elif number in nets:
            lines.append(base.label_pin(pin, x, y, nets[number]))
        else:
            raise ValueError(f"{ref} pin {number} ({name}) has no net or NC mark")
    return lines


def custom_nets(form: str, by_name: dict[str, str]) -> dict[str, str]:
    return {str(p["number"]): by_name[str(p["name"])] for p in custom_pin_records(form)}


def main() -> None:
    forms: dict[str, str] = {
        "NESPICO_GP": clone_symbol("Connector_Generic.kicad_sym", "Conn_01x23", "NESPICO_GP"),
        "NESPICO_ADC": clone_symbol("Connector_Generic.kicad_sym", "Conn_01x03", "NESPICO_ADC"),
        "NESPICO_SYS": clone_symbol("Connector_Generic.kicad_sym", "Conn_01x03", "NESPICO_SYS"),
        "NESPICO_PWR": clone_symbol("Connector_Generic.kicad_sym", "Conn_01x02", "NESPICO_PWR"),
        "FAMICOM_60": clone_symbol("Connector_Generic.kicad_sym", "Conn_02x30_Odd_Even", "FAMICOM_60"),
        "SN74AHCT244": clone_symbol("74xx.kicad_sym", "74HC244", "SN74AHCT244", "https://www.ti.com/lit/ds/symlink/sn74ahct244.pdf"),
        "SN74LVC244A": clone_symbol("74xx.kicad_sym", "74HC244", "SN74LVC244A", "https://www.ti.com/lit/ds/symlink/sn74lvc244a.pdf"),
        "SN74AHCT573": clone_symbol("74xx.kicad_sym", "74LS573", "SN74AHCT573", "https://www.ti.com/lit/ds/symlink/sn74ahct573.pdf", {"Load": "LE"}),
        "R": clone_symbol("Device.kicad_sym", "R", "R"),
        "C": clone_symbol("Device.kicad_sym", "C", "C"),
    }
    forms["SN74AHCT74"] = custom_symbol("SN74AHCT74", [
        ("1", "1CLR_N", "left", "input"), ("2", "1D", "left", "input"),
        ("3", "1CLK", "left", "input"), ("4", "1PRE_N", "left", "input"),
        ("5", "1Q", "right", "output"), ("6", "1Q_N", "right", "output"),
        ("7", "GND", "left", "power_in"), ("8", "2Q_N", "right", "output"),
        ("9", "2Q", "right", "output"), ("10", "2PRE_N", "left", "input"),
        ("11", "2CLK", "left", "input"), ("12", "2D", "left", "input"),
        ("13", "2CLR_N", "left", "input"), ("14", "VCC", "right", "power_in"),
    ], datasheet="https://www.ti.com/lit/ds/symlink/sn74ahct74.pdf")
    forms["SN74LVC257A"] = custom_symbol("SN74LVC257A", [
        ("1", "SEL", "left", "input"), ("2", "1A", "left", "input"),
        ("3", "1B", "left", "input"), ("4", "1Y", "right", "tri_state"),
        ("5", "2A", "left", "input"), ("6", "2B", "left", "input"),
        ("7", "2Y", "right", "tri_state"), ("8", "GND", "left", "power_in"),
        ("9", "3Y", "right", "tri_state"), ("10", "3A", "left", "input"),
        ("11", "3B", "left", "input"), ("12", "4Y", "right", "tri_state"),
        ("13", "4A", "left", "input"), ("14", "4B", "left", "input"),
        ("15", "OE_N", "left", "input"), ("16", "VCC", "right", "power_in"),
    ], datasheet="https://www.ti.com/lit/ds/symlink/sn74lvc257a.pdf")
    ram_pins = [
        ("1", "NC", "left", "passive"), ("2", "A12", "left", "input"),
        ("3", "A7", "left", "input"), ("4", "A6", "left", "input"),
        ("5", "A5", "left", "input"), ("6", "A4", "left", "input"),
        ("7", "A3", "left", "input"), ("8", "A2", "left", "input"),
        ("9", "A1", "left", "input"), ("10", "A0", "left", "input"),
        ("11", "DQ0", "right", "bidirectional"), ("12", "DQ1", "right", "bidirectional"),
        ("13", "DQ2", "right", "bidirectional"), ("14", "VSS", "left", "power_in"),
        ("15", "DQ3", "right", "bidirectional"), ("16", "DQ4", "right", "bidirectional"),
        ("17", "DQ5", "right", "bidirectional"), ("18", "DQ6", "right", "bidirectional"),
        ("19", "DQ7", "right", "bidirectional"), ("20", "CE_N", "left", "input"),
        ("21", "A10", "left", "input"), ("22", "OE_N", "left", "input"),
        ("23", "A11", "left", "input"), ("24", "A9", "left", "input"),
        ("25", "A8", "left", "input"), ("26", "CE2", "left", "input"),
        ("27", "WE_N", "left", "input"), ("28", "VCC", "right", "power_in"),
    ]
    forms["AS6C6264"] = custom_symbol("AS6C6264", ram_pins,
        datasheet="https://www.alliancememory.com/wp-content/uploads/Alliance-Memory_64K_AS6C6264v2.0July2017.pdf")
    # Abstract functions are non-BOM blocks, retained only to define the logical netlist.
    forms["CONTROL_EQUATIONS"] = custom_symbol("CONTROL_EQUATIONS", [
        ("1", "M2", "left", "input"), ("2", "CPU_RW", "left", "input"),
        ("3", "CPU_A15", "left", "input"), ("4", "PPU_RD_N", "left", "input"),
        ("5", "PPU_WR_N", "left", "input"), ("6", "CPU_ADDR_STB", "left", "input"),
        ("7", "PPU_ADDR_STB", "left", "input"), ("8", "CPU_PHASE", "left", "input"),
        ("9", "CPU_PHASE_N", "left", "input"), ("10", "PPU_PHASE", "left", "input"),
        ("11", "PPU_PHASE_N", "left", "input"), ("12", "RUN_N", "left", "input"),
        ("13", "PWR_GOOD", "left", "input"),
        ("14", "M2_CTRL", "right", "output"), ("15", "CPU_RW_CTRL", "right", "output"),
        ("16", "PPU_RD_N_CTRL", "right", "output"), ("17", "PPU_WR_N_CTRL", "right", "output"),
        ("18", "CPU_CART_ACTIVE", "right", "output"), ("19", "CPU_TX_OE_N", "right", "output"),
        ("20", "CPU_RX_OE_N", "right", "output"), ("21", "PPU_TX_OE_N", "right", "output"),
        ("22", "PPU_RX_OE_N", "right", "output"), ("23", "CPU_LE_LOW", "right", "output"),
        ("24", "CPU_LE_HIGH", "right", "output"), ("25", "PPU_LE_LOW", "right", "output"),
        ("26", "PPU_LE_HIGH", "right", "output"), ("27", "PPU_STATUS_EN", "right", "output"),
        ("28", "BUS_RUN", "right", "output"),
    ], bom=False, hide_pin_names=True)
    forms["INVERTER_FUNCTIONS"] = custom_symbol("INVERTER_FUNCTIONS", [
        ("1", "CPU_ADDR_STB", "left", "input"), ("2", "PPU_ADDR_STB", "left", "input"),
        ("3", "PPU_A13", "left", "input"), ("4", "CPU_RW", "left", "input"),
        ("5", "PPU_RD_N", "left", "input"), ("6", "PPU_WR_N", "left", "input"),
        ("7", "BUS_RUN", "left", "input"), ("8", "PPU_STATUS_EN", "left", "input"),
        ("9", "CPU_CART_ACTIVE", "left", "input"),
        ("10", "CPU_STB_N", "right", "output"), ("11", "PPU_STB_N", "right", "output"),
        ("12", "PPU_A13_N", "right", "output"), ("13", "CPU_RW_N", "right", "output"),
        ("14", "PPU_RD", "right", "output"), ("15", "PPU_WR", "right", "output"),
        ("16", "BUS_OE_N", "right", "output"), ("17", "PPU_STATUS_OE_N", "right", "output"),
        ("18", "ROMSEL_N", "right", "output"),
    ], bom=False, hide_pin_names=True)
    forms["POWER_BOUNDARY"] = custom_symbol("POWER_BOUNDARY", [
        ("1", "+5V_EXT", "left", "input"), ("2", "+3V3_PICO", "left", "input"),
        ("3", "RUN_N", "left", "input"), ("4", "GND", "left", "power_in"),
        ("5", "+5V_LOGIC", "right", "output"), ("6", "+5V_CART", "right", "output"),
        ("7", "PWR_GOOD", "right", "output"), ("8", "GND", "right", "power_in"),
    ], bom=False, hide_pin_names=True)
    forms["AUDIO_BOUNDARY"] = custom_symbol("AUDIO_BOUNDARY", [
        ("1", "GP22_PWM", "left", "input"), ("2", "AUDIO_RETURN", "left", "input"),
        ("3", "GND", "left", "power_in"), ("4", "AUDIO_TO_CART", "right", "output"),
        ("5", "ADC0_AUDIO", "right", "output"),
    ], bom=False, hide_pin_names=True)

    records = {name: base.pin_records(form) for name, form in forms.items()}
    lib = '(kicad_symbol_lib (version 20220914) (generator "kicad_symbol_editor")\n'
    lib += "\n".join(forms.values()) + "\n)\n"
    (HERE / f"{LIB_NAME}.kicad_sym").write_text(lib, encoding="utf-8")
    embedded = "\n".join(base.qualified_form(form, name) for name, form in forms.items())
    elements: list[str] = []
    no_connects: list[str] = []

    def add(ref: str, sym: str, value: str, x: float, y: float, nets: dict[str, str], *, abstract: bool = False,
            no_connect: set[str] | None = None, datasheet: str = "",
            ref_y: float | None = None, value_y: float | None = None) -> None:
        p = records[sym]
        by_num = {str(pin["number"]): pin for pin in p}
        by_name = {str(pin["name"]): str(pin["number"]) for pin in p}
        resolved_nets: dict[str, str] = {}
        for key, net in nets.items():
            key = str(key)
            number = key if key in by_num else by_name.get(key)
            if number is None:
                raise ValueError(f"{ref} mapping key {key!r} is not a pin number or name")
            resolved_nets[number] = net
        property_ref_y = y - 23 if ref_y is None else ref_y
        property_value_y = y + 23 if value_y is None else value_y
        elements.append(make_instance(f"{LIB_NAME}:{sym}", ref, value, x, y, p, datasheet=datasheet,
                                       ref_y=property_ref_y, value_y=property_value_y, abstract=abstract))
        no_connect = no_connect or set()
        for number, pin in by_num.items():
            px = x + float(pin["x"])
            py = y - float(pin["y"])
            if number in no_connect:
                no_connects.append(base.no_connect(px, py))
            elif number in resolved_nets:
                elements.append(base.label_pin(pin, x, y, resolved_nets[number]))
            else:
                raise ValueError(f"{ref} pin {number} ({pin['name']}) unassigned")

    # Logical Pico boundary: pins 1..23 map to GP0..GP22. The first 16 are
    # byte lanes; the remaining pins carry their functional net names.
    gpio_nets = {str(i): f"GP{i-1}" for i in range(1, 17)}
    gpio_nets.update({
        "17": "GP16_M2", "18": "GP17_CPU_RW", "19": "GP18_PPU_RD_N",
        "20": "GP19_PPU_WR_N", "21": "GP20_CPU_ADDR_STB",
        "22": "GP21_PPU_ADDR_STB", "23": "GP22_APU_AUDIO_PWM",
    })
    add("J1", "NESPICO_GP", "RP2350 GPIO 0-22 logical boundary", 35, 75, gpio_nets,
        ref_y=39, value_y=111)
    add("J2", "NESPICO_ADC", "ADC-only GP26-28", 35, 145,
        {"1": "GP26_ADC0", "2": "GP27_ADC1", "3": "GP28_ADC2"})
    add("J3", "NESPICO_SYS", "3V3 / GND / RUN_N", 35, 175,
        {"1": "+3V3_PICO", "2": "GND", "3": "RUN_N"})
    add("J4", "NESPICO_PWR", "External regulated 5V input", 35, 205,
        {"1": "+5V_EXT", "2": "GND"})

    # Functional blocks: exact implementations are left out intentionally.
    ctrl_x, ctrl_y = 115, 120
    ctrl_nets = {str(i): name for i, name in enumerate([
        "GP16_M2", "GP17_CPU_RW", "CPU_A15", "GP18_PPU_RD_N", "GP19_PPU_WR_N",
        "GP20_CPU_ADDR_STB", "GP21_PPU_ADDR_STB", "CPU_PHASE", "CPU_PHASE_N",
        "PPU_PHASE", "PPU_PHASE_N", "RUN_N", "PWR_GOOD",
        "M2_CTRL", "CPU_RW_CTRL", "PPU_RD_N_CTRL", "PPU_WR_N_CTRL", "CPU_CART_ACTIVE",
        "CPU_TX_OE_N", "CPU_RX_OE_N", "PPU_TX_OE_N", "PPU_RX_OE_N",
        "CPU_LE_LOW", "CPU_LE_HIGH", "PPU_LE_LOW", "PPU_LE_HIGH", "PPU_STATUS_EN", "BUS_RUN"
    ], start=1)}
    add("U1", "CONTROL_EQUATIONS", "Functional equations; gate pin map candidate in spec", ctrl_x, ctrl_y, ctrl_nets, abstract=True)
    inv_nets = {str(i): name for i, name in enumerate([
        "GP20_CPU_ADDR_STB", "GP21_PPU_ADDR_STB", "PPU_A13", "GP17_CPU_RW",
        "GP18_PPU_RD_N", "GP19_PPU_WR_N", "BUS_RUN", "PPU_STATUS_EN", "CPU_CART_ACTIVE",
        "CPU_STB_N", "PPU_STB_N", "PPU_A13_N", "CPU_RW_N",
        "PPU_RD", "PPU_WR", "BUS_OE_N", "PPU_STATUS_OE_N", "ROMSEL_N"
    ], start=1)}
    add("U2", "INVERTER_FUNCTIONS", "2x SN74AHCT04 candidate; pin map in spec", 115, 45, inv_nets, abstract=True)
    phase_nets = {
        "1": "BUS_RUN", "2": "CPU_PHASE_N", "3": "CPU_STB_N", "4": "+5V_LOGIC",
        "5": "CPU_PHASE", "6": "CPU_PHASE_N", "7": "GND", "8": "PPU_PHASE_N",
        "9": "PPU_PHASE", "10": "+5V_LOGIC", "11": "PPU_STB_N", "12": "PPU_PHASE_N",
        "13": "BUS_RUN", "14": "+5V_LOGIC",
    }
    add("U3", "SN74AHCT74", "Two falling-edge address phase toggles", 165, 45, phase_nets,
        datasheet="https://www.ti.com/lit/ds/symlink/sn74ahct74.pdf")
    power_nets = {"1": "+5V_EXT", "2": "+3V3_PICO", "3": "RUN_N", "4": "GND",
                  "5": "+5V_LOGIC", "6": "+5V_CART", "7": "PWR_GOOD", "8": "GND"}
    add("U4", "POWER_BOUNDARY", "Protection / current limit / enable TBD", 80, 205, power_nets, abstract=True)
    audio_nets = {"1": "GP22_APU_AUDIO_PWM", "2": "AUDIO_RETURN_FROM_CART",
                  "3": "GND", "4": "AUDIO_TO_CART", "5": "GP26_ADC0"}
    add("U5", "AUDIO_BOUNDARY", "Filter / bias / protection TBD", 80, 245, audio_nets, abstract=True)

    # CPU and PPU address latches; Q7 of the CPU high latch provides internal A15.
    def latch_nets(lane: str, byte: str) -> dict[str, str]:
        d = [f"GP{i}" for i in (range(0, 8) if lane == "CPU" else range(8, 16))]
        if byte == "LOW":
            q = [f"{lane}_A{i}" for i in range(8)]
            le = f"{lane}_LE_LOW"
        else:
            q = [f"{lane}_A{i}" for i in range(8, 16)]
            le = f"{lane}_LE_HIGH"
        pinmap = {"1": "BUS_OE_N", "10": "GND", "11": le, "20": "+5V_LOGIC"}
        for i in range(8):
            pinmap[str(i + 2)] = d[i]
            pinmap[str(19 - i)] = q[i]
        return pinmap

    for ref, lane, byte, x, y in [
        ("U6", "CPU", "LOW", 165, 95), ("U7", "CPU", "HIGH", 165, 135),
        ("U8", "PPU", "LOW", 165, 180), ("U9", "PPU", "HIGH", 165, 220),
    ]:
        nm = latch_nets(lane, byte)
        if lane == "PPU" and byte == "HIGH":
            # PPU has A8-A13 only; unused Q6/Q7 are intentionally NC.
            nm.pop("12", None)  # Q7
            nm.pop("13", None)  # Q6
            add(ref, "SN74AHCT573", "SN74AHCT573", x, y, nm, no_connect={"12", "13"},
                datasheet="https://www.ti.com/lit/ds/symlink/sn74ahct573.pdf")
        else:
            add(ref, "SN74AHCT573", "SN74AHCT573", x, y, nm,
                datasheet="https://www.ti.com/lit/ds/symlink/sn74ahct573.pdf")

    # Dedicated transmit and receive buffers. Both halves of each 244 share their OE.
    def buffer_nets(lane: str, direction: str) -> dict[str, str]:
        nets = {"1OE": f"{lane}_{direction}_OE_N", "2OE": f"{lane}_{direction}_OE_N",
                "10": "GND", "20": "+5V_LOGIC" if direction == "TX" else "+3V3_PICO"}
        for i in range(8):
            ai = f"{lane}_D{i}" if direction == "RX" else f"GP{i if lane == 'CPU' else i+8}"
            yo = (f"GP{i}" if lane == "CPU" else f"PPU_RX_D{i}") if direction == "RX" else f"{lane}_D{i}"
            aname = f"1A{i}" if i < 4 else f"2A{i-4}"
            yname = f"1Y{i}" if i < 4 else f"2Y{i-4}"
            nets[aname] = ai
            nets[yname] = yo
        return nets

    for lane, y, tx_ref, rx_ref in (("CPU", 65, "U10", "U11"), ("PPU", 155, "U12", "U13")):
        add(tx_ref, "SN74AHCT244", "SN74AHCT244 fixed Pico-to-cartridge", 225, y,
            buffer_nets(lane, "TX"), datasheet="https://www.ti.com/lit/ds/symlink/sn74ahct244.pdf")
        add(rx_ref, "SN74LVC244A", "SN74LVC244A fixed cartridge-to-Pico", 225, y + 35,
            buffer_nets(lane, "RX"), datasheet="https://www.ti.com/lit/ds/symlink/sn74lvc244a.pdf")

    # The console-facing clock/read/write/decode outputs are 5-V AHCT-buffered.
    control_buffer = {
        "1OE": "BUS_OE_N", "2OE": "BUS_OE_N", "10": "GND", "20": "+5V_LOGIC",
        "1A0": "M2_CTRL", "1Y0": "M2_5V",
        "1A1": "CPU_RW_CTRL", "1Y1": "CPU_RW_5V",
        "1A2": "PPU_RD_N_CTRL", "1Y2": "PPU_RD_N_5V",
        "1A3": "PPU_WR_N_CTRL", "1Y3": "PPU_WR_N_5V",
        "2A0": "ROMSEL_N", "2Y0": "ROMSEL_N_5V",
        "2A1": "GND", "2A2": "GND", "2A3": "GND",
    }
    control_nc = {str(pin["number"]) for pin in records["SN74AHCT244"]
                  if str(pin["name"]) in {"2Y1", "2Y2", "2Y3"}}
    add("U17", "SN74AHCT244", "SN74AHCT244 5-V control outputs", 275, 35,
        control_buffer, no_connect=control_nc,
        datasheet="https://www.ti.com/lit/ds/symlink/sn74ahct244.pdf")

    # PPU data/status selection. LVC257 inputs accept 5-V signals at 3.3-V VCC.
    mux0 = {"1": "GP18_PPU_RD_N", "15": "PPU_STATUS_OE_N", "8": "GND", "16": "+3V3_PICO"}
    mux1 = {"1": "GP18_PPU_RD_N", "15": "PPU_STATUS_OE_N", "8": "GND", "16": "+3V3_PICO"}
    for idx in range(4):
        for mux, base_i in ((mux0, 0), (mux1, 4)):
            ch = idx + 1
            bit = base_i + idx
            mux[str({1:2, 2:5, 3:10, 4:13}[ch])] = f"PPU_RX_D{bit}"
            mux[str({1:3, 2:6, 3:11, 4:14}[ch])] = ("CART_IRQ_N" if bit == 0 else
                "CIRAM_A10" if bit == 1 else "CIRAM_CE_N" if bit == 2 else "GND")
            mux[str({1:4, 2:7, 3:9, 4:12}[ch])] = f"GP{8+bit}"
    add("U14", "SN74LVC257A", "PPU data/status mux bits 0-3", 275, 75, mux0,
        datasheet="https://www.ti.com/lit/ds/symlink/sn74lvc257a.pdf")
    add("U15", "SN74LVC257A", "PPU data/status mux bits 4-7", 275, 135, mux1,
        datasheet="https://www.ti.com/lit/ds/symlink/sn74lvc257a.pdf")

    # CIRAM SRAM: 2 KiB visible via A0-A10; upper address inputs tied low.
    ram_net_by_name = {
        "NC": "NC_RAM_PIN1", "A12": "GND", "A7": "PPU_A7", "A6": "PPU_A6",
        "A5": "PPU_A5", "A4": "PPU_A4", "A3": "PPU_A3", "A2": "PPU_A2",
        "A1": "PPU_A1", "A0": "PPU_A0", "DQ0": "PPU_D0", "DQ1": "PPU_D1",
        "DQ2": "PPU_D2", "VSS": "GND", "DQ3": "PPU_D3", "DQ4": "PPU_D4",
        "DQ5": "PPU_D5", "DQ6": "PPU_D6", "DQ7": "PPU_D7", "CE_N": "CIRAM_CE_N",
        "A10": "CIRAM_A10", "OE_N": "PPU_RX_OE_N", "A11": "GND", "A9": "PPU_A9",
        "A8": "PPU_A8", "CE2": "+5V_LOGIC", "WE_N": "PPU_TX_OE_N", "VCC": "+5V_LOGIC",
    }
    ram_nets = custom_nets(forms["AS6C6264"], ram_net_by_name)
    add("U16", "AS6C6264", "AS6C6264-55PCN 8Kx8 SRAM", 275, 220, ram_nets,
        no_connect={"1"}, datasheet="https://www.alliancememory.com/wp-content/uploads/Alliance-Memory_64K_AS6C6264v2.0July2017.pdf")

    # ADC1 rail monitor: nominal 10k/10k divider, series 1k and 100nF RC.
    r_pins = records["R"]
    c_pins = records["C"]
    for ref, value, x, y, pmap in [
        ("R1", "10k", 160, 255, {"1": "+5V_CART", "2": "CART_5V_HALF"}),
        ("R2", "10k", 185, 255, {"1": "CART_5V_HALF", "2": "GND"}),
        ("R3", "1k", 210, 255, {"1": "CART_5V_HALF", "2": "GP27_ADC1"}),
    ]:
        elements.append(make_instance(f"{LIB_NAME}:R", ref, value, x, y, r_pins,
                                      ref_y=y-7, value_y=y+5))
        for p in r_pins:
            elements.append(base.label_pin(p, x, y, pmap[str(p["number"])]))
    elements.append(make_instance(f"{LIB_NAME}:C", "C1", "100n", 235, 255, c_pins,
                                  ref_y=248, value_y=260))
    for p in c_pins:
        elements.append(base.label_pin(p, 235, 255, {"1": "GP27_ADC1", "2": "GND"}[str(p["number"])]))

    # Famicom connector net table; pin 31 is intentionally NC.
    cart = {
        1:"GND",2:"CPU_A11",3:"CPU_A10",4:"CPU_A9",5:"CPU_A8",6:"CPU_A7",7:"CPU_A6",8:"CPU_A5",9:"CPU_A4",10:"CPU_A3",11:"CPU_A2",12:"CPU_A1",13:"CPU_A0",14:"CPU_RW_5V",15:"CART_IRQ_N",16:"GND",17:"PPU_RD_N_5V",18:"CIRAM_A10",19:"PPU_A6",20:"PPU_A5",21:"PPU_A4",22:"PPU_A3",23:"PPU_A2",24:"PPU_A1",25:"PPU_A0",26:"PPU_D0",27:"PPU_D1",28:"PPU_D2",29:"PPU_D3",30:"+5V_CART",32:"M2_5V",33:"CPU_A12",34:"CPU_A13",35:"CPU_A14",36:"CPU_D7",37:"CPU_D6",38:"CPU_D5",39:"CPU_D4",40:"CPU_D3",41:"CPU_D2",42:"CPU_D1",43:"CPU_D0",44:"ROMSEL_N_5V",45:"AUDIO_TO_CART",46:"AUDIO_RETURN_FROM_CART",47:"PPU_WR_N_5V",48:"CIRAM_CE_N",49:"PPU_A13_N",50:"PPU_A7",51:"PPU_A8",52:"PPU_A9",53:"PPU_A10",54:"PPU_A11",55:"PPU_A12",56:"PPU_A13",57:"PPU_D7",58:"PPU_D6",59:"PPU_D5",60:"PPU_D4"
    }
    fam_pins = records["FAMICOM_60"]
    elements.append(make_instance(f"{LIB_NAME}:FAMICOM_60", "J5", "Famicom 60-pin functional connector", 365, 150,
                                  fam_pins, ref_y=75, value_y=225))
    for pin in fam_pins:
        num = int(str(pin["number"]))
        px = 365 + float(pin["x"])
        py = 150 - float(pin["y"])
        if num == 31:
            no_connects.append(base.no_connect(px, py))
        else:
            elements.append(base.label_pin(pin, 365, 150, cart[num]))

    # Short notes keep the functional schematic honest about its remaining gates.
    elements.extend([
        base.text_block("FUNCTIONAL CIRCUIT ONLY — NO PCB / NO FABRICATION RELEASE", 25, 270, 1.2),
        base.text_block("U1/U2 are abstract; candidate gate pin map is in rev-a-circuit-spec.md. Power/protection/audio remain open.", 25, 275, 0.85),
        base.text_block("GP26-28 ADC-only; GP29 internal; pin31 NC; pin49=/PPU_A13; pin56=PPU_A13; pin18 CIRAM_A10 -> SRAM A10.", 25, 280, 0.85),
    ])

    title = "NESPICO Rev.A logical circuit candidate"
    sch = f'''(kicad_sch (version 20230121) (generator "eeschema")
  (uuid {ROOT_UUID})
  (paper "A3")
  (title_block
    (title {base.q(title)})
    (date "2026-10-12")
    (rev "LOGIC-DRAFT-0.3")
    (comment 1 "Functional schematic only; no PCB/fabrication release")
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
    (HERE / f"{PROJECT}.kicad_pro").write_text("{}\n", encoding="utf-8")
    (HERE / "sym-lib-table").write_text(f'''(sym_lib_table
  (version 7)
  (lib (name "{LIB_NAME}") (type "KiCad") (uri "${{KIPRJMOD}}/{LIB_NAME}.kicad_sym") (options "") (descr "NESPICO functional circuit symbols"))
)
''', encoding="utf-8")
    print(f"Generated {HERE / (PROJECT + '.kicad_sch')}")
    print(f"Generated {HERE / (LIB_NAME + '.kicad_sym')}")


if __name__ == "__main__":
    main()
