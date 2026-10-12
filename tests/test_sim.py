import unittest

from nespico.sim import (
    BusEvent, CartridgeState, Mmc3A12Filter, TimingConfig,
    make_events, simulate, usb_fits,
)


class BusTests(unittest.TestCase):
    def test_one_scanline_event_counts(self):
        events = make_events(1)
        self.assertEqual(sum(e.bus == "ppu" for e in events), 168)
        self.assertGreater(sum(e.bus == "cpu" for e in events), 100)

    def test_full_frame_fetch_count(self):
        events = make_events(262)
        self.assertEqual(sum(e.bus == "ppu" for e in events), 241 * 168)

    def test_nominal_model_fits(self):
        cfg = TimingConfig()
        result = simulate(make_events(262, cfg), cfg)
        self.assertEqual(result.deadline_misses, 0)
        self.assertGreater(result.cpu_ppu_overlaps, 0)

    def test_slow_model_detects_failures(self):
        cfg = TimingConfig(sys_mhz=20, propagation_ns=160)
        self.assertGreater(simulate(make_events(4, cfg), cfg).deadline_misses, 0)

    def test_shared_bus_stress_detects_contention(self):
        cfg = TimingConfig(shared_engine=True, cpu_service_cycles=48, ppu_service_cycles=48)
        self.assertGreater(simulate(make_events(2, cfg), cfg).deadline_misses, 0)

    def test_events_sorted(self):
        events = make_events(2)
        self.assertEqual([e.time_ns for e in events], sorted(e.time_ns for e in events))

    def test_zero_scanlines_rejected(self):
        with self.assertRaises(ValueError):
            make_events(0)

    def test_deadline_derived_from_event(self):
        cfg = TimingConfig(cpu_service_cycles=30)
        self.assertEqual(simulate([BusEvent(0, "cpu", 10, 0)], cfg).deadline_misses, 1)


class CartridgeTests(unittest.TestCase):
    def test_reset_preserves_ram(self):
        state = CartridgeState()
        state.insert("Tennis")
        state.ram[0x20] = 0x99
        state.insert("Super Mario Bros.")
        state.reset()
        self.assertEqual(state.ram[0x20], 0x99)
        self.assertEqual(state.reset_count, 1)

    def test_power_cycle_clears_ram_in_model(self):
        state = CartridgeState()
        state.ram[1] = 18
        state.power_cycle()
        self.assertEqual(state.ram[1], 0)

    def test_mmc3_rise_needs_three_low_m2_edges(self):
        f = Mmc3A12Filter()
        self.assertFalse(f.m2_falling_edge(False))
        self.assertFalse(f.m2_falling_edge(False))
        self.assertFalse(f.m2_falling_edge(True))
        self.assertEqual(f.rises, 0)
        for _ in range(3):
            f.m2_falling_edge(False)
        self.assertTrue(f.m2_falling_edge(True))
        self.assertEqual(f.rises, 1)
        self.assertFalse(f.m2_falling_edge(True))

    def test_usb_uncompressed_frame_exceeds_budget(self):
        self.assertFalse(usb_fits(256 * 240, fps=60))
        self.assertTrue(usb_fits(4_000, fps=60))


if __name__ == "__main__":
    unittest.main()
