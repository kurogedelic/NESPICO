#!/usr/bin/env python3
"""Conservative shape-aware copper-clearance screen for the bring-up PCB.

Requires pcbnew and Shapely in the same Python environment. This is a
supplementary screen, not a replacement for KiCad's native DRC.
"""
from __future__ import annotations

from pathlib import Path

import pcbnew
from shapely.affinity import rotate
from shapely.geometry import LineString, Point, box

PCB = Path(__file__).resolve().with_name("NESPICO_8bit_fixture.kicad_pcb")
CLEARANCE_MM = 0.20
RESOLUTION = 16
F_CU = pcbnew.F_Cu
B_CU = pcbnew.B_Cu
MM = pcbnew.ToMM


def pad_geometry(pad):
    x = MM(pad.GetPosition().x)
    y = MM(pad.GetPosition().y)
    sx = MM(pad.GetSize().x)
    sy = MM(pad.GetSize().y)
    shape = pad.GetShape()

    if shape == pcbnew.PAD_SHAPE_CIRCLE or abs(sx - sy) < 1e-5:
        copper = Point(x, y).buffer(max(sx, sy) / 2, resolution=RESOLUTION)
    elif shape == pcbnew.PAD_SHAPE_OVAL:
        if sx >= sy:
            centerline = LineString([(x - (sx - sy) / 2, y),
                                     (x + (sx - sy) / 2, y)])
            radius = sy / 2
        else:
            centerline = LineString([(x, y - (sy - sx) / 2),
                                     (x, y + (sy - sx) / 2)])
            radius = sx / 2
        copper = centerline.buffer(radius, cap_style="round", resolution=RESOLUTION)
        angle = float(pad.GetOrientationDegrees())
        if angle:
            copper = rotate(copper, angle, origin=(x, y), use_radians=False)
    else:
        # Rectangular bounding shape is conservative for round-rect/trapezoid
        # pads; the current standard footprints use circles, ovals, or rectangles.
        copper = box(x - sx / 2, y - sy / 2, x + sx / 2, y + sy / 2)
        angle = float(pad.GetOrientationDegrees())
        if angle:
            copper = rotate(copper, angle, origin=(x, y), use_radians=False)
    return copper.buffer(CLEARANCE_MM / 2, resolution=RESOLUTION)


def track_geometry(track):
    width = MM(track.GetWidth())
    if isinstance(track, pcbnew.PCB_VIA):
        p = track.GetPosition()
        copper = Point(MM(p.x), MM(p.y)).buffer(width / 2, resolution=RESOLUTION)
        layers = "both"
    else:
        a = track.GetStart()
        b = track.GetEnd()
        centerline = LineString([(MM(a.x), MM(a.y)), (MM(b.x), MM(b.y))])
        copper = centerline.buffer(width / 2, cap_style="round", resolution=RESOLUTION)
        layers = track.GetLayer()
    return copper.buffer(CLEARANCE_MM / 2, resolution=RESOLUTION), layers


def describe(kind, obj):
    if kind == "pad":
        return f"{obj[0]}.{obj[1]}"
    a = obj.GetStart()
    b = obj.GetEnd()
    return tuple(round(MM(v), 3) for v in (a.x, a.y, b.x, b.y))


def main() -> int:
    board = pcbnew.LoadBoard(str(PCB))
    if board is None:
        raise SystemExit(f"FAIL: could not load {PCB}")

    items = []
    for track in board.GetTracks():
        geometry, layers = track_geometry(track)
        items.append(("track", track.GetNetCode(), layers, geometry, track))
    pads = 0
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            items.append(("pad", pad.GetNetCode(), pad.GetLayerSet(),
                          pad_geometry(pad),
                          (footprint.GetReference(), pad.GetNumber(), pad)))
            pads += 1

    violations = []
    pairs_checked = 0
    for i, first in enumerate(items):
        kind_a, net_a, layer_a, geom_a, obj_a = first
        for second in items[i + 1:]:
            kind_b, net_b, layer_b, geom_b, obj_b = second
            if net_a and net_a == net_b:
                continue

            if kind_a == "track" and kind_b == "track":
                if layer_a != "both" and layer_b != "both" and layer_a != layer_b:
                    continue
            elif kind_a == "pad" and kind_b == "pad":
                pad_a = obj_a[2]
                pad_b = obj_b[2]
                common_layer = any(
                    pad_a.GetLayerSet().Contains(layer)
                    and pad_b.GetLayerSet().Contains(layer)
                    for layer in (F_CU, B_CU)
                )
                if not common_layer:
                    continue
            else:
                track = obj_a if kind_a == "track" else obj_b
                pad_entry = obj_b if kind_a == "track" else obj_a
                pad = pad_entry[2]
                if (not isinstance(track, pcbnew.PCB_VIA)
                        and not pad.GetLayerSet().Contains(track.GetLayer())):
                    continue

            pairs_checked += 1
            if geom_a.intersects(geom_b):
                violations.append((kind_a, net_a, describe(kind_a, obj_a),
                                   kind_b, net_b, describe(kind_b, obj_b)))

    print(f"tracks/vias={len(board.GetTracks())}; pads={pads}; "
          f"relevant pairs={pairs_checked}; clearance={CLEARANCE_MM:.2f} mm; "
          f"violations={len(violations)}")
    for violation in violations[:80]:
        print("VIOLATION", violation)
    if violations:
        return 1
    print("PASS: no detected different-net copper overlap or spacing below threshold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
