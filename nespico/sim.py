"""Deterministic feasibility model, NOT actual PIO execution or a NES emulator."""

from dataclasses import dataclass
from math import ceil

CPU_HZ = 1_789_773
PPU_HZ = 5_369_318
DOTS_PER_SCANLINE = 341
SCANLINES = 262


@dataclass(frozen=True)
class BusEvent:
    time_ns: float
    bus: str
    deadline_ns: float
    address: int


@dataclass(frozen=True)
class TimingConfig:
    sys_mhz: float = 150.0
    cpu_service_cycles: int = 12
    ppu_service_cycles: int = 12
    propagation_ns: float = 22.0
    cpu_deadline_ns: float = 320.0
    ppu_deadline_ns: float = 180.0
    shared_engine: bool = False

    def service_ns(self, bus: str) -> float:
        cycles = self.cpu_service_cycles if bus == "cpu" else self.ppu_service_cycles
        return cycles * (1_000.0 / self.sys_mhz) + self.propagation_ns


@dataclass(frozen=True)
class SimResult:
    cpu: int
    ppu: int
    deadline_misses: int
    worst_lateness_ns: float
    worst_latency_ns: float
    cpu_ppu_overlaps: int


def make_events(scanlines: int = SCANLINES, config: TimingConfig | None = None) -> list[BusEvent]:
    """Representative NTSC CPU cycles and PPU fetches, not a full NES bus trace.

    PPU memory fetches approximated every two dots during rendering,
    including nametable, attribute, background pattern and sprite intervals.
    """
    if not 1 <= scanlines <= SCANLINES:
        raise ValueError("scanlines must be 1..262")
    config = config or TimingConfig()
    cpu_period = 1e9 / CPU_HZ
    dot_period = 1e9 / PPU_HZ
    duration = scanlines * DOTS_PER_SCANLINE * dot_period
    events = []
    for cycle in range(ceil(duration / cpu_period)):
        t = cycle * cpu_period
        if t < duration:
            events.append(BusEvent(t, "cpu", config.cpu_deadline_ns, cycle & 0x7FFF))
    for line in range(scanlines):
        if line >= 240 and line != 261:
            continue
        offset = line * DOTS_PER_SCANLINE * dot_period
        for dot in range(1, 337, 2):
            addr = (0x1000 if dot % 8 in (5, 7) else 0x2000) + (dot & 0xFF)
            events.append(BusEvent(offset + dot * dot_period, "ppu", config.ppu_deadline_ns, addr))
    return sorted(events, key=lambda e: (e.time_ns, e.bus))


def simulate(events: list[BusEvent], config: TimingConfig) -> SimResult:
    """Abstract dual engines or shared engine with deadline tracking.

    Assumes bus transaction addresses and data are already prepared.
    The resulting deadline pass is NOT proof of real PIO or emulator timing.
    """
    available = {"cpu": 0.0, "ppu": 0.0, "shared": 0.0}
    active_until = {"cpu": 0.0, "ppu": 0.0}
    cpu = ppu = misses = overlaps = 0
    worst_late = worst_latency = 0.0
    for event in events:
        engine = "shared" if config.shared_engine else event.bus
        start = max(event.time_ns, available[engine])
        end = start + config.service_ns(event.bus)
        available[engine] = end
        latency = end - event.time_ns
        late = max(0.0, latency - event.deadline_ns)
        misses += late > 1e-7
        worst_late = max(worst_late, late)
        worst_latency = max(worst_latency, latency)
        if event.bus == "cpu":
            cpu += 1
        else:
            ppu += 1
        other = "ppu" if event.bus == "cpu" else "cpu"
        if event.time_ns < active_until[other]:
            overlaps += 1
        active_until[event.bus] = max(active_until[event.bus], end)
    return SimResult(cpu, ppu, misses, worst_late, worst_latency, overlaps)


class CartridgeState:
    """Motherboard RAM survives RESET and inserted-cartridge changes."""

    def __init__(self):
        self.ram = bytearray(2048)
        self.cartridge = None
        self.reset_count = 0

    def insert(self, cartridge: str) -> None:
        self.cartridge = cartridge

    def reset(self) -> None:
        self.reset_count += 1

    def power_cycle(self) -> None:
        self.ram[:] = b"\0" * 2048
        self.reset_count = 0


class Mmc3A12Filter:
    """Partial M2-qualified A12 low filter, NOT full MMC3 banking/IRQ."""

    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self.low_m2_count = 0
        self.last_a12 = False
        self.rises = 0

    def m2_falling_edge(self, a12: bool) -> bool:
        if not a12:
            self.low_m2_count += 1
        valid = a12 and not self.last_a12 and self.low_m2_count >= self.threshold
        if valid:
            self.rises += 1
        if a12:
            self.low_m2_count = 0
        self.last_a12 = a12
        return valid


def usb_fits(bytes_per_frame: int, fps: float = 60.0, throughput: int = 1_000_000) -> bool:
    """Budget check with ASSUMED application-level USB throughput."""
    return bytes_per_frame * fps <= throughput
