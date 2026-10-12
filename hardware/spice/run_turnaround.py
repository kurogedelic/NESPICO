#!/usr/bin/env python3
"""Run a bounded ngspice sweep for a one-bit NESPICO bus turnaround model.

The model is a switch-level screening aid, not a vendor transistor-level model
or electrical/timing sign-off. See README.md beside this script.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "bus_turnaround.cir.in"
CART_RELEASE_NS = [0, 10, 20, 30, 50]
GUARD_NS = [0, 4, 8, 12, 20, 32, 40]
AHCT_ENABLE_NS = 13
LVC_DISABLE_NS = 8
SWITCH_EDGE_MARGIN_NS = 0.1
AHCT_OUTPUT_GUIDANCE_A = 0.025
NO_OVERLAP_CURRENT_THRESHOLD_A = 0.001
MEASUREMENTS = (
    "cart_conflict_peak",
    "mcu_conflict_peak",
    "cart_write_low",
    "mcu_write_low",
)


def render_deck(template: str, *, cart_release: int, guard: int) -> str:
    values = {
        "cart_release_ns": str(cart_release + 100),
        "tx_enable_ns": str(100 + guard + AHCT_ENABLE_NS),
        "rx_disable_ns": str(100 + LVC_DISABLE_NS),
        "mcu_enable_ns": str(100 + guard + SWITCH_EDGE_MARGIN_NS),
    }
    deck = template
    for key, value in values.items():
        deck = deck.replace("${" + key + "}", value)
    if "${" in deck:
        raise ValueError("unresolved template token in SPICE deck")
    return deck


def parse_measurements(output: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for name in MEASUREMENTS:
        match = re.search(
            rf"^\s*{re.escape(name)}\s*=\s*([-+0-9.eE]+)",
            output,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        if not match:
            raise RuntimeError(f"ngspice did not report {name}\n{output[-3000:]}")
        values[name] = float(match.group(1))
    return values


def run_case(ngspice: str, deck_text: str) -> tuple[dict[str, float], str]:
    with tempfile.TemporaryDirectory(prefix="nespico-spice-") as tmp:
        deck_path = Path(tmp) / "case.cir"
        deck_path.write_text(deck_text, encoding="utf-8")
        result = subprocess.run(
            [ngspice, "-b", str(deck_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            raise RuntimeError(f"ngspice failed with exit {result.returncode}\n{output[-3000:]}")
        return parse_measurements(output), output


def draw_svg(rows: list[dict[str, float]], out: Path) -> None:
    """Write a dependency-free SVG showing peak current vs guard delay."""
    width, height = 900, 560
    left, right, top, bottom = 90, 30, 55, 80
    plot_w, plot_h = width - left - right, height - top - bottom
    max_guard = max(GUARD_NS)
    max_ma = max(55.0, max(r["cart_conflict_peak_A"] * 1000 for r in rows),
                 max(r["mcu_conflict_peak_A"] * 1000 for r in rows))
    max_ma = ((int(max_ma / 10) + 1) * 10)

    def x(v: float) -> float:
        return left + (v / max_guard) * plot_w

    def y(v: float) -> float:
        return top + plot_h - (v / max_ma) * plot_h

    colors = ["#2563eb", "#059669", "#d97706", "#7c3aed", "#be123c"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#111827}.muted{fill:#6b7280}.grid{stroke:#d1d5db;stroke-width:1}</style>',
        '<text x="90" y="27" font-size="20" font-weight="bold">Cartridge-side contention vs. break-before-make guard</text>',
    ]
    for i in range(0, int(max_ma) + 1, 10):
        yy = y(i)
        parts.append(f'<line class="grid" x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}"/>')
        parts.append(f'<text x="{left-12}" y="{yy+4:.1f}" text-anchor="end" font-size="12">{i}</text>')
    for tick in range(0, max_guard + 1, 4):
        xx = x(tick)
        parts.append(f'<line class="grid" x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{height-bottom}" opacity="0.55"/>')
        parts.append(f'<text x="{xx:.1f}" y="{height-bottom+22}" text-anchor="middle" font-size="12">{tick}</text>')
    parts.extend([
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#111827"/>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#111827"/>',
        f'<line x1="{left}" y1="{y(AHCT_OUTPUT_GUIDANCE_A*1000):.1f}" x2="{width-right}" y2="{y(AHCT_OUTPUT_GUIDANCE_A*1000):.1f}" stroke="#dc2626" stroke-dasharray="6 5"/>',
        f'<text x="{width-right-4}" y="{y(AHCT_OUTPUT_GUIDANCE_A*1000)-7:.1f}" text-anchor="end" font-size="12" fill="#dc2626">25 mA TI AHCT244 recommendation (per output)</text>',
        f'<text x="{left + plot_w/2:.1f}" y="{height-22}" text-anchor="middle" font-size="14">Guard delay after direction-change request (ns)</text>',
        f'<text x="22" y="{top + plot_h/2:.1f}" text-anchor="middle" font-size="14" transform="rotate(-90 22 {top + plot_h/2:.1f})">Cartridge source current (mA)</text>',
    ])

    legend_y = height - bottom + 48
    legend_x = left
    for release, color in zip(CART_RELEASE_NS, colors):
        series = sorted((r for r in rows if r["cart_release_ns"] == release), key=lambda r: r["guard_ns"])
        points = " ".join(f'{x(r["guard_ns"]):.1f},{y(r["cart_conflict_peak_A"]*1000):.1f}' for r in series)
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for r in series:
            parts.append(f'<circle cx="{x(r["guard_ns"]):.1f}" cy="{y(r["cart_conflict_peak_A"]*1000):.1f}" r="3.2" fill="{color}"/>')
        parts.append(f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x+24}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<text x="{legend_x+30}" y="{legend_y+4}" font-size="12">cart release {release} ns</text>')
        legend_x += 155
    parts.append('<text x="90" y="520" font-size="11" class="muted">Cartridge-side branch only; MCU-side overlap is summarized separately. Switch-level assumptions are not validated device limits.</text>')
    parts.append('</svg>')
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ngspice", default=shutil.which("ngspice"), help="ngspice executable")
    parser.add_argument("--outdir", type=Path, default=HERE / "results", help="output directory")
    args = parser.parse_args()
    if not args.ngspice:
        parser.error("ngspice was not found; install it or pass --ngspice")

    template = TEMPLATE.read_text(encoding="utf-8")
    args.outdir.mkdir(parents=True, exist_ok=True)
    deck_dir = args.outdir / "representative_decks"
    deck_dir.mkdir(exist_ok=True)
    rows: list[dict[str, float]] = []
    saved = {(20, 0), (20, 8), (50, 40)}

    for release in CART_RELEASE_NS:
        for guard in GUARD_NS:
            deck = render_deck(template, cart_release=release, guard=guard)
            measurements, output = run_case(args.ngspice, deck)
            row = {
                "cart_release_ns": release,
                "guard_ns": guard,
                "ahct_enable_delay_ns": AHCT_ENABLE_NS,
                "lvc_disable_delay_ns": LVC_DISABLE_NS,
                "cart_conflict_peak_A": measurements["cart_conflict_peak"],
                "mcu_conflict_peak_A": measurements["mcu_conflict_peak"],
                "cart_write_low_V": measurements["cart_write_low"],
                "mcu_write_low_V": measurements["mcu_write_low"],
            }
            if row["cart_conflict_peak_A"] < -1e-6 or row["mcu_conflict_peak_A"] < -1e-6:
                raise RuntimeError(f"unexpected negative current measurement: {row}")
            if row["cart_write_low_V"] > 0.8 or row["mcu_write_low_V"] > 0.8:
                raise RuntimeError(f"steady-state low did not reach the expected model level: {row}")

            cart_overlap = guard + AHCT_ENABLE_NS < release
            mcu_overlap = guard < LVC_DISABLE_NS
            if cart_overlap and row["cart_conflict_peak_A"] < NO_OVERLAP_CURRENT_THRESHOLD_A:
                raise RuntimeError(f"expected a modeled cart-driver overlap: {row}")
            if not cart_overlap and row["cart_conflict_peak_A"] > NO_OVERLAP_CURRENT_THRESHOLD_A:
                raise RuntimeError(f"unexpected modeled cart contention without overlap: {row}")
            if mcu_overlap and row["mcu_conflict_peak_A"] < NO_OVERLAP_CURRENT_THRESHOLD_A:
                raise RuntimeError(f"expected a modeled MCU-side driver overlap: {row}")
            if not mcu_overlap and row["mcu_conflict_peak_A"] > NO_OVERLAP_CURRENT_THRESHOLD_A:
                raise RuntimeError(f"unexpected modeled MCU-side contention without overlap: {row}")

            rows.append(row)
            if (release, guard) in saved:
                tag = f"cart_release_{release}ns_guard_{guard}ns"
                (deck_dir / f"{tag}.cir").write_text(deck, encoding="utf-8")
                clean_log = "\n".join(line.rstrip() for line in output.splitlines()) + "\n"
                (deck_dir / f"{tag}.log").write_text(clean_log, encoding="utf-8")

    csv_path = args.outdir / "turnaround_sweep.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "model_type": "switch-level behavioral, not a vendor transistor-level model",
        "cart_release_ns_sweep": CART_RELEASE_NS,
        "guard_ns_sweep": GUARD_NS,
        "ahct_enable_delay_ns": AHCT_ENABLE_NS,
        "lvc_disable_delay_ns": LVC_DISABLE_NS,
        "ideal_switch_edge_margin_ns": SWITCH_EDGE_MARGIN_NS,
        "ahct244_recommended_per_output_current_mA": AHCT_OUTPUT_GUIDANCE_A * 1000,
        "no_overlap_current_detection_threshold_mA": NO_OVERLAP_CURRENT_THRESHOLD_A * 1000,
        "assumptions": {
            "cart_driver_equivalent_ohms": 50,
            "ahct_low_equivalent_ohms": 55,
            "lvc_output_equivalent_ohms": 50,
            "rp2350_output_equivalent_ohms_placeholder": 50,
            "load_capacitance_each_node_pF": 50,
            "cartridge_release_delay_is_assumed_not_specified": True,
        },
        "cases": len(rows),
        "max_cart_conflict_mA": max(r["cart_conflict_peak_A"] for r in rows) * 1000,
        "max_mcu_conflict_mA": max(r["mcu_conflict_peak_A"] for r in rows) * 1000,
        "rows": rows,
    }
    (args.outdir / "turnaround_sweep.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    draw_svg(rows, args.outdir / "turnaround_sweep.svg")

    safe_by_release = {}
    for release in CART_RELEASE_NS:
        safe = [r["guard_ns"] for r in rows if r["cart_release_ns"] == release
                and r["cart_conflict_peak_A"] < NO_OVERLAP_CURRENT_THRESHOLD_A
                and r["mcu_conflict_peak_A"] < NO_OVERLAP_CURRENT_THRESHOLD_A]
        safe_by_release[str(release)] = min(safe) if safe else None
    safe_mcu = [r["guard_ns"] for r in rows
                if r["mcu_conflict_peak_A"] < NO_OVERLAP_CURRENT_THRESHOLD_A]
    report = [
        "# Turnaround SPICE screening results",
        "",
        "Generated by `run_turnaround.py`; 35 ngspice transient cases passed the script's assertions.",
        "",
        "| Assumed cartridge-output release | Smallest tested guard with neither modeled path contending |",
        "| ---: | ---: |",
    ]
    for release, guard in safe_by_release.items():
        report.append(f"| {release} ns | {guard if guard is not None else 'not found'} ns |")
    report.extend([
        "",
        f"The MCU-side illustrative LVC/RP driver overlap peaks at about **{max(r['mcu_conflict_peak_A'] for r in rows)*1000:.1f} mA** in the sweep and is avoided at a tested guard of **{min(safe_mcu)} ns** or longer.",
        "The model uses 13 ns AHCT output-enable delay and 8 ns LVC output-disable delay at 50 pF as datasheet-based delay inputs. The cartridge driver's release time and all equivalent output resistances are explicit assumptions.",
        "The guard table requires both modeled source branches to remain below a 1 mA overlap-detection threshold. The 25 mA comparison line is TI's SN74AHCT244 recommended per-output load guidance (50 mA total for that part), not a current limit for the LVC244A or RP2350.",
        "",
        "A zero modeled overlap is a timing condition in this abstract circuit only. It does not establish actual cartridge release timing, real output current, signal integrity, safe pin mapping, power-off behavior, or hardware suitability. Measure exact cartridge/device behavior and review the selected module and complete datasheets before any PCB release.",
        "",
        "See `turnaround_sweep.csv`, `turnaround_sweep.svg`, and `representative_decks/` for raw data and reproduced cases.",
    ])
    (args.outdir / "turnaround-summary.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"ngspice cases: {len(rows)}; output: {args.outdir}")
    for release, guard in safe_by_release.items():
        print(f"cart release {release} ns -> min tested guard {guard} ns")
    print(f"MCU side min tested guard: {min(safe_mcu)} ns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
