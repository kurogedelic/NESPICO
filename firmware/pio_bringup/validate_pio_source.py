#!/usr/bin/env python3
"""Check that the loopback PIO source and firmware timing constants agree.

This is a source-level consistency check, not a PIO emulator or hardware test.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PIO = HERE / "pio" / "loopback.pio"
DEFAULT_C = HERE / "main.c"
EXPECTED = [
    ("pull block", 0),
    ("set x, 31", 0),
    ("out pins, 1", 0),
    ("in pins, 1", 1),
    ("jmp x-- loop", 0),
    ("push block", 0),
]


def parse_source(text: str) -> tuple[list[tuple[str, int]], dict[str, int], list[str]]:
    instructions: list[tuple[str, int]] = []
    labels: dict[str, int] = {}
    directives: list[str] = []
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("."):
            directives.append(re.sub(r"\s+", " ", line))
            continue
        label = re.fullmatch(r"([A-Za-z_]\w*):", line)
        if label:
            name = label.group(1)
            if name in labels:
                raise ValueError(f"duplicate PIO label: {name}")
            labels[name] = len(instructions)
            continue
        match = re.fullmatch(r"(.+?)\s+side\s+(\d+)", line)
        if not match:
            raise ValueError(f"unrecognized PIO source line: {raw.strip()}")
        opcode = re.sub(r"\s+", " ", match.group(1).strip())
        instructions.append((opcode, int(match.group(2))))
    return instructions, labels, directives


def check(pio_path: Path, c_path: Path) -> int:
    instructions, labels, directives = parse_source(pio_path.read_text(encoding="utf-8"))
    expected_directives = [".program loopback", ".side_set 1", ".wrap_target", ".wrap"]
    if directives != expected_directives:
        raise SystemExit(f"PIO directives mismatch: expected {expected_directives}, got {directives}")
    if labels != {"loop": 2}:
        raise SystemExit(f"PIO loop label mismatch: expected {{'loop': 2}}, got {labels}")
    if instructions != EXPECTED:
        raise SystemExit(f"PIO instruction/side-set mismatch: expected {EXPECTED}, got {instructions}")

    main = c_path.read_text(encoding="utf-8")
    constants = {"TEST_WORDS": 4096, "FIFO_DEPTH": 4}
    for name, expected_value in constants.items():
        definitions = re.findall(rf"(?m)^\s*#\s*define\s+{re.escape(name)}\b(.*)$", main)
        if len(definitions) != 1:
            raise SystemExit(f"{name} definition count mismatch: expected 1, got {len(definitions)}")
        match = re.fullmatch(r"\s*(\d+)u\s*", definitions[0])
        if not match:
            raise SystemExit(f"{name} must be an unsigned integer literal, got {definitions[0].strip()!r}")
        if int(match.group(1)) != expected_value:
            actual = match.group(1)
            raise SystemExit(f"{name} mismatch: expected {expected_value}, got {actual}")

    # PULL + SET, then OUT/IN/JMP for 32 bits, then PUSH.
    clocks_per_word = 2 + 32 * 3 + 1
    definitions = re.findall(r"(?m)^\s*#\s*define\s+PIO_CLOCKS_PER_WORD\b(.*)$", main)
    if len(definitions) != 1:
        raise SystemExit(f"PIO_CLOCKS_PER_WORD definition count mismatch: expected 1, got {len(definitions)}")
    match = re.fullmatch(r"\s*(\d+)u\s*", definitions[0])
    if not match:
        raise SystemExit(f"PIO_CLOCKS_PER_WORD must be an unsigned integer literal, got {definitions[0].strip()!r}")
    if int(match.group(1)) != clocks_per_word:
        actual = match.group(1)
        raise SystemExit(f"PIO_CLOCKS_PER_WORD mismatch: expected {clocks_per_word}, got {actual}")

    print("PIO source consistency: PASS")
    print(f"  assembled source operations: {len(instructions)}")
    print("  serial loop: 32 bits; sample strobe asserted only on IN")
    print(f"  nominal instruction clocks per word: {clocks_per_word}")
    print("  firmware constants: TEST_WORDS=4096, FIFO_DEPTH=4")
    print("  hardware timing, FIFO behavior, and GPIO electrical behavior are not tested")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pio", type=Path, default=DEFAULT_PIO, help="PIO assembly source")
    parser.add_argument("--c-source", type=Path, default=DEFAULT_C, help="firmware C source")
    args = parser.parse_args()
    return check(args.pio, args.c_source)


if __name__ == "__main__":
    raise SystemExit(main())
