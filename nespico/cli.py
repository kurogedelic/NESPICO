"""Run a hypothetical NTSC cartridge bus timing test on the host."""
import argparse
import json
from dataclasses import asdict

from nespico.sim import TimingConfig, make_events, simulate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scanlines", type=int, default=262)
    parser.add_argument("--sys-mhz", type=float, default=150.0)
    parser.add_argument("--pio-cycles", type=int, default=12)
    parser.add_argument("--settle-ns", type=float, default=22.0)
    parser.add_argument("--shared-bus", action="store_true")
    args = parser.parse_args()
    if args.sys_mhz <= 0 or args.pio_cycles < 1 or args.settle_ns < 0:
        parser.error("clock and cycles must be positive; settle time nonnegative")
    cfg = TimingConfig(sys_mhz=args.sys_mhz, cpu_service_cycles=args.pio_cycles,
                       ppu_service_cycles=args.pio_cycles, propagation_ns=args.settle_ns,
                       shared_engine=args.shared_bus)
    report = simulate(make_events(args.scanlines, cfg), cfg)
    print(json.dumps({"assumptions": asdict(cfg), "result": asdict(report)}, indent=2))
    return 1 if report.deadline_misses else 0


if __name__ == "__main__":
    raise SystemExit(main())
