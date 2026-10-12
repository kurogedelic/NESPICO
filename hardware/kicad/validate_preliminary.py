#!/usr/bin/env python3
"""Validate the intended electrical connectivity of the draft KiCad slice."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMATIC = HERE / "NESPICO_Interface.kicad_sch"

EXPECTED_COMPONENTS = {
    "U1": "SN74AHCT244",
    "U2": "SN74LVC244A",
    "R1": "10k",
    "R2": "10k",
    "C1": "100n",
    "C2": "100n",
}
EXPECTED_NETS = {
    "/CART_D0": {("U1", "18"), ("U2", "2")},
    "/MCU_D0": {("U1", "2"), ("U2", "18")},
    "/TX_OE_N": {("U1", "1"), ("R1", "1")},
    "/RX_OE_N": {("U2", "1"), ("R2", "1")},
    "/+5V_BUFFER": {("U1", "20"), ("C1", "1")},
    "/+3V3_LOGIC": {
        ("U1", "19"), ("U2", "19"), ("U2", "20"),
        ("R1", "2"), ("R2", "2"), ("C2", "1"),
    },
}
EXPECTED_GND = {
    (ref, pin)
    for ref in ("U1", "U2")
    for pin in ("10", "4", "6", "8", "11", "13", "15", "17")
} | {("C1", "2"), ("C2", "2")}
EXPECTED_NC_OUTPUTS = {
    (ref, pin)
    for ref in ("U1", "U2")
    for pin in ("3", "5", "7", "9", "12", "14", "16")
}


def check(cli: str) -> None:
    if not SCHEMATIC.exists():
        raise SystemExit(f"missing schematic: {SCHEMATIC}")
    with tempfile.TemporaryDirectory(prefix="nespico-kicad-check-") as temp:
        netlist_path = Path(temp) / "draft.xml"
        run = subprocess.run(
            [cli, "sch", "export", "netlist", "--format", "kicadxml", str(SCHEMATIC), "-o", str(netlist_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if run.returncode:
            raise SystemExit(f"kicad-cli failed ({run.returncode}):\n{run.stdout}\n{run.stderr}")
        root = ET.parse(netlist_path).getroot()

    components = {
        comp.attrib["ref"]: comp.findtext("value", default="")
        for comp in root.findall("./components/comp")
    }
    if components != EXPECTED_COMPONENTS:
        raise SystemExit(f"component inventory mismatch: {components}")

    nets: dict[str, set[tuple[str, str]]] = {}
    for net in root.findall("./nets/net"):
        nets[net.attrib["name"]] = {
            (node.attrib["ref"], node.attrib["pin"])
            for node in net.findall("node")
        }
    for name, expected in EXPECTED_NETS.items():
        actual = nets.get(name)
        if actual != expected:
            raise SystemExit(f"net {name} mismatch: expected {expected}, got {actual}")

    gnd = nets.get("/GND", set())
    if not EXPECTED_GND.issubset(gnd):
        raise SystemExit(f"GND missing expected pins: {EXPECTED_GND - gnd}")

    nc_outputs = {
        node
        for name, nodes in nets.items()
        if name.startswith("unconnected-")
        for node in nodes
        if node in EXPECTED_NC_OUTPUTS
    }
    if nc_outputs != EXPECTED_NC_OUTPUTS:
        raise SystemExit(f"unused output NC set mismatch: {nc_outputs}")

    # Each active output-enable net must contain only one chip OE and its 10k pull-up.
    for name, chip in (("/TX_OE_N", "U1"), ("/RX_OE_N", "U2")):
        if len(nets[name]) != 2 or (chip, "1") not in nets[name]:
            raise SystemExit(f"unsafe or ambiguous enable net {name}: {nets[name]}")

    print("KiCad netlist connectivity: PASS")
    print(f"  components: {len(components)}; named nets: {len(nets)}")
    print("  D0 transmit/receive directions, separate OE controls, and rail connections: PASS")
    print(f"  tied-low unused inputs: {len(EXPECTED_GND) - 4}; no-connect unused outputs: {len(nc_outputs)}")
    print("  footprints and board-specific pin numbers remain intentionally blank")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default=shutil.which("kicad-cli"), help="KiCad CLI executable")
    args = parser.parse_args()
    if not args.kicad_cli:
        parser.error("kicad-cli was not found; install KiCad or pass --kicad-cli")
    check(args.kicad_cli)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
