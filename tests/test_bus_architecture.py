"""Regression tests comparing independent and multiplexed CPU/PPU bus engines.

These are checks on an assumed scheduler, not measured RP2350 timing.
"""
import unittest
from nespico.sim import TimingConfig, make_events, simulate


class ArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = make_events(262)

    def test_nominal_dual_engines_meet_assumed_deadlines(self):
        result = simulate(self.frame, TimingConfig())
        self.assertEqual(result.cpu, 29781)
        self.assertEqual(result.ppu, 40970)
        self.assertEqual(result.deadline_misses, 0)
        self.assertGreater(result.cpu_ppu_overlaps, 10000)

    def test_serialized_engine_misses_assumed_deadlines(self):
        result = simulate(self.frame, TimingConfig(shared_engine=True))
        self.assertGreater(result.deadline_misses, 10000)
        self.assertGreater(result.worst_latency_ns, 180)

    def test_shared_engine_is_not_inherently_impossible(self):
        # Faster PIO transactions can fit even with one serialized engine.
        fast = TimingConfig(shared_engine=True, cpu_service_cycles=10, ppu_service_cycles=10)
        self.assertEqual(simulate(self.frame, fast).deadline_misses, 0)

    def test_48_cycle_dual_engines_are_not_fast_enough(self):
        slow = TimingConfig(cpu_service_cycles=48, ppu_service_cycles=48)
        self.assertGreater(simulate(self.frame, slow).deadline_misses, 0)


if __name__ == "__main__":
    unittest.main()
