"""Software-only invariants for the abstract shared data-bus owner guard."""
from itertools import product
import unittest

from nespico.bus_safety import (
    BreakBeforeMake,
    BusOwner,
    BusTransfer,
    requested_owner,
)


class BusSafetyTests(unittest.TestCase):
    def assert_exclusive(self, state):
        self.assertFalse(state.console_oe and state.cartridge_oe)

    def test_console_read_and_write_assign_opposite_owners(self):
        self.assertIs(requested_owner(BusTransfer.CONSOLE_READ), BusOwner.CARTRIDGE)
        self.assertIs(requested_owner(BusTransfer.CONSOLE_WRITE), BusOwner.CONSOLE)
        self.assertIs(requested_owner(BusTransfer.IDLE), BusOwner.DISABLED)

    def test_invalid_transfer_is_rejected(self):
        with self.assertRaises(TypeError):
            requested_owner("read")

    def test_startup_is_disabled_and_requires_guard_step(self):
        sequencer = BreakBeforeMake()
        first = sequencer.advance(BusOwner.CARTRIDGE)
        self.assertIs(first.owner, BusOwner.DISABLED)
        self.assertTrue(first.guard_pending)
        self.assert_exclusive(first)

        second = sequencer.advance(BusOwner.CARTRIDGE)
        self.assertIs(second.owner, BusOwner.CARTRIDGE)
        self.assertTrue(second.cartridge_oe)
        self.assertFalse(second.console_oe)
        self.assert_exclusive(second)

    def test_direction_change_has_a_disabled_step(self):
        sequencer = BreakBeforeMake()
        sequencer.advance(BusOwner.CONSOLE)
        writing = sequencer.advance(BusOwner.CONSOLE)
        self.assertIs(writing.owner, BusOwner.CONSOLE)

        turnaround = sequencer.advance(BusOwner.CARTRIDGE)
        self.assertIs(turnaround.owner, BusOwner.DISABLED)
        self.assertTrue(turnaround.guard_pending)
        self.assert_exclusive(turnaround)

        reading = sequencer.advance(BusOwner.CARTRIDGE)
        self.assertIs(reading.owner, BusOwner.CARTRIDGE)
        self.assert_exclusive(reading)

    def test_idle_and_inhibit_disable_immediately_and_cancel_pending_grant(self):
        sequencer = BreakBeforeMake()
        sequencer.advance(BusOwner.CARTRIDGE)
        idle = sequencer.advance(None)
        self.assertIs(idle.owner, BusOwner.DISABLED)
        self.assertFalse(idle.guard_pending)

        sequencer.advance(BusOwner.CONSOLE)
        reset = sequencer.advance(BusOwner.CONSOLE, inhibited=True)
        self.assertIs(reset.owner, BusOwner.DISABLED)
        self.assertFalse(reset.guard_pending)

        recovery = sequencer.advance(BusOwner.CONSOLE)
        self.assertIs(recovery.owner, BusOwner.DISABLED)
        self.assertTrue(recovery.guard_pending)
        self.assertIs(sequencer.advance(BusOwner.CONSOLE).owner, BusOwner.CONSOLE)

    def test_changing_target_during_guard_restarts_guard(self):
        sequencer = BreakBeforeMake()
        self.assertTrue(sequencer.advance(BusOwner.CARTRIDGE).guard_pending)
        changed = sequencer.advance(BusOwner.CONSOLE)
        self.assertIs(changed.owner, BusOwner.DISABLED)
        self.assertTrue(changed.guard_pending)
        self.assertIs(sequencer.advance(BusOwner.CONSOLE).owner, BusOwner.CONSOLE)

    def test_invalid_owner_is_rejected(self):
        with self.assertRaises(TypeError):
            BreakBeforeMake().advance("cartridge")

    def test_all_five_step_sequences_preserve_owner_and_guard_invariants(self):
        requests = (BusOwner.CONSOLE, BusOwner.CARTRIDGE, BusOwner.DISABLED, None)
        actions = tuple(product(requests, (False, True)))
        active = (BusOwner.CONSOLE, BusOwner.CARTRIDGE)

        # 8 possible request/inhibit combinations at each step: exhaustively
        # check every five-step history, not only hand-picked examples.
        for sequence in product(actions, repeat=5):
            sequencer = BreakBeforeMake()
            previous_owner = BusOwner.DISABLED
            for requested, inhibited in sequence:
                state = sequencer.advance(requested, inhibited=inhibited)
                self.assert_exclusive(state)
                self.assertEqual(state.console_oe, state.owner is BusOwner.CONSOLE)
                self.assertEqual(state.cartridge_oe, state.owner is BusOwner.CARTRIDGE)

                if inhibited or requested in (None, BusOwner.DISABLED):
                    self.assertIs(state.owner, BusOwner.DISABLED)
                    self.assertFalse(state.guard_pending)
                elif state.owner is BusOwner.DISABLED:
                    self.assertTrue(state.guard_pending)

                if previous_owner in active and requested in active and requested is not previous_owner and not inhibited:
                    self.assertIs(state.owner, BusOwner.DISABLED)
                previous_owner = state.owner


if __name__ == "__main__":
    unittest.main()
