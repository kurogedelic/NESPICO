"""Regression tests for the PIO source and firmware timing consistency check."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIRMWARE_DIR = ROOT / "firmware" / "pio_bringup"
sys.path.insert(0, str(FIRMWARE_DIR))

from validate_pio_source import check, parse_source  # noqa: E402


PIO_PATH = FIRMWARE_DIR / "pio" / "loopback.pio"
C_PATH = FIRMWARE_DIR / "main.c"


class PioSourceTests(unittest.TestCase):
    def setUp(self):
        self.pio_text = PIO_PATH.read_text(encoding="utf-8")
        self.c_text = C_PATH.read_text(encoding="utf-8")

    def check_text(self, pio_text=None, c_text=None):
        with tempfile.TemporaryDirectory(prefix="nespico-pio-test-") as temp:
            pio_path = Path(temp) / "loopback.pio"
            c_path = Path(temp) / "main.c"
            pio_path.write_text(pio_text if pio_text is not None else self.pio_text,
                                encoding="utf-8")
            c_path.write_text(c_text if c_text is not None else self.c_text,
                              encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                return check(pio_path, c_path)

    def test_repository_sources_pass(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(check(PIO_PATH, C_PATH), 0)

    def test_parser_reports_exact_instruction_sequence(self):
        instructions, labels, directives = parse_source(self.pio_text)
        self.assertEqual(instructions, [
            ("pull block", 0),
            ("set x, 31", 0),
            ("out pins, 1", 0),
            ("in pins, 1", 1),
            ("jmp x-- loop", 0),
            ("push block", 0),
        ])
        self.assertEqual(labels, {"loop": 2})
        self.assertEqual(directives,
                         [".program loopback", ".side_set 1", ".wrap_target", ".wrap"])

    def test_sample_strobe_side_set_mutation_is_rejected(self):
        changed = self.pio_text.replace("in pins, 1 side 1", "in pins, 1 side 0")
        with self.assertRaisesRegex(SystemExit, "instruction/side-set mismatch"):
            self.check_text(pio_text=changed)

    def test_duplicate_directive_is_rejected(self):
        changed = self.pio_text.replace(".wrap\n", ".wrap\n.wrap\n")
        with self.assertRaisesRegex(SystemExit, "directives mismatch"):
            self.check_text(pio_text=changed)

    def test_duplicate_label_is_rejected(self):
        changed = self.pio_text.replace("loop:\n", "loop:\nloop:\n")
        with self.assertRaisesRegex(ValueError, "duplicate PIO label: loop"):
            self.check_text(pio_text=changed)

    def test_firmware_count_and_clock_mutations_are_rejected(self):
        for name, old, new in (
            ("TEST_WORDS", "4096u", "4095u"),
            ("FIFO_DEPTH", "4u", "3u"),
            ("PIO_CLOCKS_PER_WORD", "99u", "98u"),
        ):
            with self.subTest(name=name):
                changed = self.c_text.replace(f"#define {name} {old}",
                                              f"#define {name} {new}")
                with self.assertRaisesRegex(SystemExit, f"{name} mismatch"):
                    self.check_text(c_text=changed)

    def test_duplicate_firmware_constant_is_rejected(self):
        changed = self.c_text.replace(
            "#define FIFO_DEPTH 4u",
            "#define FIFO_DEPTH 4u\n#define FIFO_DEPTH 3u",
        )
        with self.assertRaisesRegex(SystemExit, "FIFO_DEPTH definition count mismatch"):
            self.check_text(c_text=changed)

    def test_non_literal_firmware_constant_is_rejected(self):
        changed = self.c_text.replace("#define FIFO_DEPTH 4u", "#define FIFO_DEPTH (4u)")
        with self.assertRaisesRegex(SystemExit, "unsigned integer literal"):
            self.check_text(c_text=changed)

    def test_unrecognized_pio_line_is_rejected(self):
        changed = self.pio_text.replace("    push block side 0", "    push block")
        with self.assertRaisesRegex(ValueError, "unrecognized PIO source line"):
            self.check_text(pio_text=changed)


if __name__ == "__main__":
    unittest.main()
