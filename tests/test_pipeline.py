"""Check headroom once CPU/PPU address computation is included."""
import unittest
from nespico.sim import TimingConfig, make_events, simulate
from nespico.pipeline import simulate_pipeline


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = make_events(262)

    def test_zero_producer_cost_matches_timing_only_model(self):
        cfg = TimingConfig()
        simple = simulate(self.events, cfg)
        pipeline = simulate_pipeline(self.events, cfg)
        self.assertEqual(simple.deadline_misses, pipeline.deadline_misses)
        self.assertAlmostEqual(simple.worst_latency_ns, pipeline.worst_latency_ns)

    def test_small_independent_producer_fits_assumed_window(self):
        result = simulate_pipeline(self.events, TimingConfig(), 10, 10)
        self.assertEqual(result.deadline_misses, 0)

    def test_ppu_producer_cost_can_break_nominal_bus_model(self):
        result = simulate_pipeline(self.events, TimingConfig(), 10, 16)
        self.assertGreater(result.ppu_misses, 0)
        self.assertEqual(result.cpu_misses, 0)

    def test_cpu_producer_cost_can_break_nominal_bus_model(self):
        result = simulate_pipeline(self.events, TimingConfig(), 40, 10)
        self.assertGreater(result.cpu_misses, 0)
        self.assertEqual(result.ppu_misses, 0)

    def test_invalid_producer_cost_rejected(self):
        with self.assertRaises(ValueError):
            simulate_pipeline(self.events[:1], TimingConfig(), -1, 0)


if __name__ == "__main__":
    unittest.main()
