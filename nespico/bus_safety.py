"""Abstract bidirectional-bus ownership guard; not a hardware timing model.

This module models only which side may drive a shared data bus. It deliberately
assigns no GPIOs, PIO instructions, strobe relationships, or physical dead time.
"""

from dataclasses import dataclass
from enum import Enum


class BusOwner(Enum):
    """The exclusive owner of a connector-facing data bus."""

    DISABLED = "disabled"
    CONSOLE = "console"
    CARTRIDGE = "cartridge"


class BusTransfer(Enum):
    """A data transfer viewed from the console's perspective."""

    IDLE = "idle"
    CONSOLE_READ = "console_read"
    CONSOLE_WRITE = "console_write"


def requested_owner(transfer: BusTransfer) -> BusOwner:
    """Return the required bus owner for a CPU or PPU data transfer.

    A console read means the cartridge drives the data bus; a console write
    means the console drives it. Callers must request IDLE when the connector
    is not participating in the current transaction.
    """
    if not isinstance(transfer, BusTransfer):
        raise TypeError("transfer must be a BusTransfer")
    if transfer is BusTransfer.CONSOLE_READ:
        return BusOwner.CARTRIDGE
    if transfer is BusTransfer.CONSOLE_WRITE:
        return BusOwner.CONSOLE
    return BusOwner.DISABLED


@dataclass(frozen=True)
class BusDriveState:
    """Logical output-enable request; not a claim about electrical pin state."""

    owner: BusOwner
    guard_pending: bool = False

    @property
    def console_oe(self) -> bool:
        return self.owner is BusOwner.CONSOLE

    @property
    def cartridge_oe(self) -> bool:
        return self.owner is BusOwner.CARTRIDGE


class BreakBeforeMake:
    """Require one complete disabled sequencer step before enabling a driver.

    The first request for an owner (including after a direction change) returns
    both OEs disabled. Repeating the same request on the next step grants that
    owner. IDLE or inhibit disables immediately and cancels any pending grant.
    The duration and placement of a step relative to real bus strobes are
    intentionally unspecified and must be established by hardware validation.
    """

    def __init__(self) -> None:
        self._owner = BusOwner.DISABLED
        self._pending: BusOwner | None = None

    def advance(
        self, requested: BusOwner | None, *, inhibited: bool = False
    ) -> BusDriveState:
        if requested is not None and not isinstance(requested, BusOwner):
            raise TypeError("requested must be a BusOwner or None")

        if inhibited or requested in (None, BusOwner.DISABLED):
            self._owner = BusOwner.DISABLED
            self._pending = None
            return BusDriveState(self._owner)

        if self._owner is requested:
            self._pending = None
            return BusDriveState(self._owner)

        self._owner = BusOwner.DISABLED
        if self._pending is requested:
            self._owner = requested
            self._pending = None
            return BusDriveState(self._owner)

        self._pending = requested
        return BusDriveState(self._owner, guard_pending=True)
