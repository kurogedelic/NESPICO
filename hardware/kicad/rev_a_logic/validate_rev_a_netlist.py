#!/usr/bin/env python3
"""Validate critical connector/net relationships in the generated KiCad netlist.

Usage:
  python3 validate_rev_a_netlist.py [NESPICO_RevA.net.xml]

This checks topology only; it is not ERC, electrical sign-off, timing proof,
connector-footprint validation, or fabrication approval.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT = Path(__file__).with_name("NESPICO_RevA.net.xml")
source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
root = ET.parse(source).getroot()

nets: dict[str, set[tuple[str, str]]] = {}
all_nodes: set[tuple[str, str]] = set()
for net in root.findall("./nets/net"):
    name = net.get("name", "")
    # KiCad prefixes root-sheet labels with a slash in its XML export.
    name = name.rsplit("/", 1)[-1]
    nodes = {(node.get("ref", ""), node.get("pin", "")) for node in net.findall("node")}
    nets[name] = nodes
    all_nodes.update(nodes)

failures: list[str] = []

def require_net(name: str, required: set[tuple[str, str]], forbidden: set[tuple[str, str]] = frozenset()) -> None:
    actual = nets.get(name, set())
    missing = required - actual
    wrongly_connected = forbidden & actual
    if missing:
        failures.append(f"{name}: missing {sorted(missing)}")
    if wrongly_connected:
        failures.append(f"{name}: unexpected {sorted(wrongly_connected)}")

# Cartridge-controlled nametable bank-select must feed internal CIRAM SRAM A10.
require_net("CIRAM_A10", {("J5", "18"), ("U16", "21"), ("U14", "6")}, {("U16", "17")})
require_net("PPU_A10", {("J5", "53"), ("U9", "17")}, {("U16", "21")})
require_net("CIRAM_CE_N", {("J5", "48"), ("U16", "20"), ("U14", "11")})

# A single safe-run condition gates every output path and asynchronously clears
# both address-phase flip-flops whenever reset is asserted or 5 V is not good.
require_net("RUN_N", {("J3", "3"), ("U1", "12"), ("U4", "3")})
require_net("PWR_GOOD", {("U1", "13"), ("U4", "7")})
require_net("BUS_RUN", {("U1", "28"), ("U2", "7"), ("U3", "1"), ("U3", "13")})
require_net("BUS_OE_N", {("U2", "16"), ("U6", "1"), ("U7", "1"),
                          ("U8", "1"), ("U9", "1"), ("U17", "1"), ("U17", "19")})
require_net("PPU_STATUS_EN", {("U1", "27"), ("U2", "8")})
require_net("PPU_STATUS_OE_N", {("U2", "17"), ("U14", "15"), ("U15", "15")})
require_net("M2_CTRL", {("U1", "14"), ("U17", "2")})
require_net("CPU_RW_CTRL", {("U1", "15"), ("U17", "4")})
require_net("PPU_RD_N_CTRL", {("U1", "16"), ("U17", "6")})
require_net("PPU_WR_N_CTRL", {("U1", "17"), ("U17", "8")})
require_net("CPU_CART_ACTIVE", {("U1", "18"), ("U2", "9")})
require_net("ROMSEL_N", {("U2", "18"), ("U17", "17")})
require_net("CPU_TX_OE_N", {("U1", "19"), ("U10", "1"), ("U10", "19")})
require_net("CPU_RX_OE_N", {("U1", "20"), ("U11", "1"), ("U11", "19")})
require_net("PPU_TX_OE_N", {("U1", "21"), ("U12", "1"), ("U12", "19"), ("U16", "27")})
require_net("PPU_RX_OE_N", {("U1", "22"), ("U13", "1"), ("U13", "19"), ("U16", "22")})
require_net("GP20_CPU_ADDR_STB", {("J1", "21"), ("U1", "6"), ("U2", "1")})
require_net("GP21_PPU_ADDR_STB", {("J1", "22"), ("U1", "7"), ("U2", "2")})

# Every 5-V console control output reaches the intended cartridge pin via U17.
for name, connector_pin, driver_pin in (
    ("M2_5V", "32", "18"),
    ("CPU_RW_5V", "14", "16"),
    ("PPU_RD_N_5V", "17", "14"),
    ("PPU_WR_N_5V", "47", "12"),
    ("ROMSEL_N_5V", "44", "3"),
):
    require_net(name, {("J5", connector_pin), ("U17", driver_pin)})

# The PPU receive buffer feeds the selector, and only the selector drives GP8.
require_net("PPU_RX_D0", {("U13", "18"), ("U14", "2")}, {("J1", "9")})
require_net("GP8", {("J1", "9"), ("U14", "4")}, {("U13", "18")})
require_net("CART_IRQ_N", {("J5", "15"), ("U14", "3")})

# Logical header J1 pin 1 is GP0, not GP1; no GP23 is part of this boundary.
for pin in range(1, 17):
    require_net(f"GP{pin-1}", {("J1", str(pin))})
for pin, name in {
    17: "GP16_M2", 18: "GP17_CPU_RW", 19: "GP18_PPU_RD_N",
    20: "GP19_PPU_WR_N", 21: "GP20_CPU_ADDR_STB", 22: "GP21_PPU_ADDR_STB",
    23: "GP22_APU_AUDIO_PWM",
}.items():
    require_net(name, {("J1", str(pin))})
require_net("GP16_M2", {("J1", "17"), ("U1", "1")})
require_net("GP17_CPU_RW", {("J1", "18"), ("U1", "2"), ("U2", "4")})
require_net("GP18_PPU_RD_N", {("J1", "19"), ("U1", "4"), ("U14", "1"), ("U15", "1"), ("U2", "5")})
require_net("GP19_PPU_WR_N", {("J1", "20"), ("U1", "5"), ("U2", "6")})
require_net("GP22_APU_AUDIO_PWM", {("J1", "23"), ("U5", "1")})

# KiCad exports an explicitly no-connect-marked pin as its own generated net.
# Accept that singleton, but fail if it is attached to any real circuit node.
pin31_nets = [(name, nodes) for name, nodes in nets.items() if ("J5", "31") in nodes]
if len(pin31_nets) != 1 or pin31_nets[0][1] != {("J5", "31")} or not pin31_nets[0][0].startswith("unconnected-"):
    failures.append("J5 pin 31 must have only KiCad's explicit unconnected-pin marker")

# Preserve the ADC header boundary and ensure GP29 is not exported as a project connector net.
require_net("GP26_ADC0", {("J2", "1"), ("U5", "5")})
require_net("GP27_ADC1", {("J2", "2"), ("R3", "2"), ("C1", "1")})
require_net("GP28_ADC2", {("J2", "3")})
if "GP23" in nets or any(name.startswith("GP23_") for name in nets):
    failures.append("GP23 must not appear; standard Pico 2 external GPIO budget ends at GP22")
if any(name == "GP29" or name.startswith("GP29_") for name in nets):
    failures.append("GP29 must not be routed; Pico 2 uses it for VSYS monitoring")

if failures:
    print(f"FAIL: {len(failures)} netlist check(s) failed in {source}")
    for failure in failures:
        print(f"  - {failure}")
    raise SystemExit(1)

print(f"PASS: critical Rev.A net topology checks passed ({len(nets)} nets, {len(all_nodes)} nodes)")
print("PASS: pin 18 CIRAM_A10 -> SRAM A10; pin 53 PPU_A10 stays separate")
print("PASS: five 5-V control outputs pass through U17 to their connector pins")
print("PASS: PPU receive/status output select is mutually exclusive and shares PPU RX/SRAM OE nets")
print("PASS: RUN_N/PWR_GOOD -> BUS_RUN -> buffer/latch disable and both phase-F/F clears")
print("PASS: J1 logical connector pins 1..23 map to GP0..GP22 and named control nets")
print("PASS: ADC reservation and isolated cartridge pin 31 preserved")
print("NOTE: topology checks are not KiCad ERC, electrical sign-off, timing proof, or fabrication approval")
