"""Conservative request-computation to PIO-bus deadline simulation.

No actual PIO code, DMA FIFOs, CPU/PPU emulator, or measured GPIO latency.
"""
from dataclasses import dataclass

from .sim import BusEvent, TimingConfig


@dataclass(frozen=True)
class PipelineResult:
    cpu: int
    ppu: int
    deadline_misses: int
    cpu_misses: int
    ppu_misses: int
    worst_lateness_ns: float
    worst_latency_ns: float


def simulate_pipeline(
    events: list[BusEvent],
    config: TimingConfig,
    cpu_prepare_cycles: int = 0,
    ppu_prepare_cycles: int = 0,
    shared_producer: bool = False,
) -> PipelineResult:
    """Conservative producer -> PIO bus pipeline budget.

    The simulated producer starts computing an address when the bus request
    arrives, then passes it to the bus engine. Real software sometimes
    prepares values earlier; this intentionally models NO lookahead.
    DMA/FIFO setup overhead, controller logic, and output-pin routing
    are not included.
    """
    if cpu_prepare_cycles < 0 or ppu_prepare_cycles < 0 or config.sys_mhz <= 0:
        raise ValueError("Invalid clock or negative producer cost")
    producers = {"cpu": 0.0, "ppu": 0.0, "shared": 0.0}
    buses = {"cpu": 0.0, "ppu": 0.0, "shared": 0.0}
    cpu = ppu = cpu_miss = ppu_miss = 0
    worst_late = worst_latency = 0.0
    ns_per_clk = 1000.0 / config.sys_mhz
    for event in sorted(events, key=lambda x: (x.time_ns, x.bus)):
        if event.bus not in ("cpu", "ppu"):
            raise ValueError("Unknown bus")
        producer = "shared" if shared_producer else event.bus
        cycles = cpu_prepare_cycles if event.bus == "cpu" else ppu_prepare_cycles
        ready = max(event.time_ns, producers[producer]) + cycles * ns_per_clk
        producers[producer] = ready
        bus = "shared" if config.shared_engine else event.bus
        done = max(ready, buses[bus]) + config.service_ns(event.bus)
        buses[bus] = done
        latency = done - event.time_ns
        late = max(0.0, latency - event.deadline_ns)
        worst_late = max(worst_late, late)
        worst_latency = max(worst_latency, latency)
        if event.bus == "cpu":
            cpu += 1
            cpu_miss += late > 1e-7
        else:
            ppu += 1
            ppu_miss += late > 1e-7
    return PipelineResult(cpu, ppu, cpu_miss + ppu_miss, cpu_miss, ppu_miss,
                          worst_late, worst_latency)
