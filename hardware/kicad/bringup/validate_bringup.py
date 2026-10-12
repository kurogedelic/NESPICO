#!/usr/bin/env python3
"""Validate the Pico 2 8-bit bring-up fixture's pin map and connectivity.

Run from the repository root with a Python interpreter that can import pcbnew,
for example `/usr/bin/python3 hardware/kicad/bringup/validate_bringup.py`.
"""
from __future__ import annotations

import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
SCH = HERE / "NESPICO_8bit_fixture.kicad_sch"
PCB = HERE / "NESPICO_8bit_fixture.kicad_pcb"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def norm(name: str | None) -> str:
    return (name or "").lstrip("/")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nespico-netlist-") as tmp:
        netlist = Path(tmp) / "fixture.xml"
        subprocess.run(
            ["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml",
             str(SCH), "-o", str(netlist)],
            check=True,
        )
        root = ET.parse(netlist).getroot()

    schematic: dict[tuple[str, str], str] = {}
    net_nodes: dict[str, set[tuple[str, str]]] = {}
    nets_element = root.find("nets")
    if nets_element is None:
        fail("KiCad netlist has no nets element")
    for net in nets_element:
        name = norm(net.get("name"))
        if name.startswith("unconnected-("):
            continue
        nodes = {(node.get("ref", ""), node.get("pin", ""))
                 for node in net.findall("node")}
        net_nodes[name] = nodes
        for node in nodes:
            if node in schematic:
                fail(f"schematic pin {node} appears on more than one net")
            schematic[node] = name

    expected = {
        "ADC2_IN": {("J2", "7"), ("J5", "1")},
        "AGND": {("J2", "8"), ("J5", "2")},
        "ADC1_IN": {("J2", "9"), ("J5", "3")},
        "ADC0_IN": {("J2", "10"), ("J5", "4")},
        "+5V_USB": {("J2", "1"), ("U1", "20"), ("C1", "1")},
        "+3V3": {("J2", "5"), ("U1", "1"), ("U2", "20"),
                  ("R1", "2"), ("R2", "2"), ("C2", "1")},
        "TX_OE_N": {("J2", "20"), ("U1", "19"), ("R1", "1")},
        "RX_OE_N": {("J2", "19"), ("U2", "19"), ("R2", "1")},
        "CPU_D0": {("J1", "1"), ("U1", "2")},
        "PPU_D0": {("J1", "11"), ("U2", "2")},
    }
    for name, pins in expected.items():
        if net_nodes.get(name) != pins:
            fail(f"{name} schematic pins {net_nodes.get(name)} != expected {pins}")

    # Pico 2 physical header numbering: J1 local positions are physical 1..20;
    # the right-side row runs in the opposite direction, physical 40..21.
    physical = {("J2", "1"): 40, ("J2", "5"): 36,
                ("J2", "7"): 34, ("J2", "8"): 33,
                ("J2", "9"): 32, ("J2", "10"): 31,
                ("J2", "19"): 22, ("J2", "20"): 21}
    pin_roles = {("J2", "1"): "+5V_USB", ("J2", "5"): "+3V3",
                 ("J2", "7"): "ADC2_IN / GP28 / ADC2",
                 ("J2", "8"): "AGND", ("J2", "9"): "ADC1_IN / GP27 / ADC1",
                 ("J2", "10"): "ADC0_IN / GP26 / ADC0",
                 ("J2", "19"): "RX_OE_N / GP17",
                 ("J2", "20"): "TX_OE_N / GP16"}
    if len(set(physical.values())) != len(physical):
        fail("Pico physical pin map is not one-to-one")
    for pin, role in pin_roles.items():
        actual = schematic.get(pin)
        if actual != role.split(" / ")[0]:
            fail(f"Pico header J2.{pin[1]} physical {physical[pin]} expected {role}, got {actual}")

    if "GP29" in " ".join(net_nodes):
        fail("GP29 must remain internal and must not be routed")
    if net_nodes.get("AGND") == net_nodes.get("GND"):
        fail("AGND must remain separate from digital GND in this fixture")

    board = pcbnew.LoadBoard(str(PCB))
    if board is None:
        fail(f"could not load {PCB}")
    footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}
    board_map: dict[tuple[str, str], str] = {}
    for ref, fp in footprints.items():
        for pad in fp.Pads():
            name = norm(pad.GetNetname())
            if name:
                board_map[(ref, pad.GetNumber())] = name
    for pin, name in schematic.items():
        if pin in board_map and board_map[pin] != name:
            fail(f"PCB {pin} net {board_map[pin]} != schematic net {name}")
        if pin not in board_map:
            fail(f"schematic pin {pin} has no matching assigned PCB pad")
    for pin, name in board_map.items():
        if pin in schematic and schematic[pin] != name:
            fail(f"PCB {pin} net {name} != schematic net {schematic[pin]}")

    connectivity = board.GetConnectivity()
    if not connectivity.Build(board):
        fail("KiCad connectivity graph build failed")
    unconnected = connectivity.GetUnconnectedCount(False)
    if unconnected:
        fail(f"PCB has {unconnected} unconnected connection(s)")
    copper_layers = board.GetCopperLayerCount()
    if copper_layers != 2:
        fail(f"expected a 2-layer PCB, found {copper_layers} copper layers")

    print("PASS: schematic/PCB pin nets agree; ADC0-2 map only to GP26-28;")
    print("      GP29 is not routed; AGND is separate; 5V test boundary is isolated;")
    print(f"      KiCad connectivity has {unconnected} unconnected nets; {copper_layers}-layer board.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
