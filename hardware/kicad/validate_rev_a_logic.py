#!/usr/bin/env python3
"""Exhaustive Boolean checks for the NESPICO Rev.A circuit candidate.

This verifies intended logic equations only. It is not an electrical, timing,
KiCad ERC, or hardware validation.
"""
from itertools import product


def main() -> None:
    checks = 0

    def check(condition: bool) -> None:
        nonlocal checks
        checks += 1
        assert condition

    # The digital GPIO partition must consume GP0..22 and leave ADC/VSYS alone.
    digital = set(range(23))
    adc = {26, 27, 28}
    internal = {29}
    check(digital == set(range(23)))
    check(digital.isdisjoint(adc | internal))
    check(adc.isdisjoint(internal))

    # Reset is released high; outputs only run when 5-V power is good.
    for run_n, pwr_good in product((False, True), repeat=2):
        bus_run = run_n and pwr_good
        bus_oe_n = not bus_run
        phase_clr_n = bus_run
        check(bus_run == (run_n and pwr_good))
        check(bus_oe_n == (not bus_run))
        check(phase_clr_n == bus_run)
        if not run_n or not pwr_good:
            check(bus_oe_n and not phase_clr_n)

    # CPU GP0..7 are borrowed to load address bytes. During that strobe,
    # disable both data directions, force M2 low, R/W high, and /ROMSEL high.
    for bus_run, m2, a15, rw, addr_stb in product((False, True), repeat=5):
        cpu_stb_n = not addr_stb
        cpu_stb_run = bus_run and cpu_stb_n
        m2_ctrl = cpu_stb_run and m2
        cpu_cart_active = m2_ctrl and a15
        romsel_n = not cpu_cart_active
        cpu_rw_n = not rw
        cpu_rw_ctrl = not (cpu_rw_n and cpu_stb_n)  # NAND
        cpu_tx = cpu_cart_active and not rw
        cpu_rx = cpu_cart_active and rw
        cpu_tx_oe_n = not cpu_tx
        cpu_rx_oe_n = not cpu_rx
        check(m2_ctrl == (bus_run and not addr_stb and m2))
        check(romsel_n == (not (bus_run and not addr_stb and m2 and a15)))
        check(cpu_rw_ctrl == (rw or addr_stb))
        check(not (not cpu_tx_oe_n and not cpu_rx_oe_n))
        if not cpu_cart_active:
            check(cpu_tx_oe_n and cpu_rx_oe_n)
        if addr_stb:
            check(not m2_ctrl and romsel_n and cpu_rw_ctrl)
            check(cpu_tx_oe_n and cpu_rx_oe_n)

    # PPU GP8..15 are borrowed for PPU address loading. Both data directions
    # and the status mux are Hi-Z during that strobe. Status is also Hi-Z during
    # reads, when the receive buffer drives this same Pico-side lane.
    for bus_run, rd_n, wr_n, addr_stb in product((False, True), repeat=4):
        ppu_stb_n = not addr_stb
        ppu_stb_run = bus_run and ppu_stb_n
        ppu_read_base = ppu_stb_run and not rd_n
        ppu_write_base = ppu_stb_run and rd_n
        ppu_read = ppu_read_base and wr_n
        ppu_write = ppu_write_base and not wr_n
        ppu_rx_oe_n = not ppu_read
        ppu_tx_oe_n = not ppu_write
        ppu_status_en = ppu_write_base and wr_n
        ppu_status_oe_n = not ppu_status_en
        ppu_rd_n_ctrl = rd_n or addr_stb
        ppu_wr_n_ctrl = wr_n or addr_stb
        status_mux_enabled = not ppu_status_oe_n
        check(not (ppu_read and ppu_write))
        check(not (not ppu_rx_oe_n and not ppu_tx_oe_n))
        check(not (status_mux_enabled and not ppu_rx_oe_n))
        check(not (status_mux_enabled and not ppu_tx_oe_n))
        check(status_mux_enabled == (bus_run and not addr_stb and rd_n and wr_n))
        if ppu_read or ppu_write or addr_stb or not bus_run:
            check(not status_mux_enabled)
        if addr_stb:
            check(ppu_rd_n_ctrl and ppu_wr_n_ctrl)
            check(ppu_rx_oe_n and ppu_tx_oe_n and not status_mux_enabled)

    # SRAM /OE and /WE share PPU receive/transmit active-low enables.
    for bus_run, rd_n, wr_n, addr_stb in product((False, True), repeat=4):
        ppu_read = bus_run and not addr_stb and not rd_n and wr_n
        ppu_write = bus_run and not addr_stb and rd_n and not wr_n
        ppu_rx_oe_n = not ppu_read
        ppu_tx_oe_n = not ppu_write
        sram_oe_n = ppu_rx_oe_n
        sram_we_n = ppu_tx_oe_n
        check(sram_oe_n == (not ppu_read))
        check(sram_we_n == (not ppu_write))
        check(not (not sram_oe_n and not sram_we_n))
        if bus_run and not addr_stb and not rd_n and wr_n:
            check(not sram_oe_n and sram_we_n)
        elif bus_run and not addr_stb and rd_n and not wr_n:
            check(sram_oe_n and not sram_we_n)
        else:
            check(sram_oe_n and sram_we_n)

    # Both address banks have mutually-exclusive LEs; CPU and PPU phases are
    # independent even when their address strobes overlap.
    for bus_run, cpu_phase, ppu_phase, cpu_stb, ppu_stb in product((False, True), repeat=5):
        cpu_low = bus_run and cpu_stb and not cpu_phase
        cpu_high = bus_run and cpu_stb and cpu_phase
        ppu_low = bus_run and ppu_stb and not ppu_phase
        ppu_high = bus_run and ppu_stb and ppu_phase
        check(not (cpu_low and cpu_high))
        check(not (ppu_low and ppu_high))
        check((cpu_low or cpu_high) == (bus_run and cpu_stb))
        check((ppu_low or ppu_high) == (bus_run and ppu_stb))

    # Every completed pair of address strobes returns its own phase to low.
    for initial_phase in (False, True):
        phase = initial_phase
        for _ in range(2):
            strobe = True
            check((strobe and not phase) ^ (strobe and phase))
            strobe = False
            check(not (strobe and not phase) and not (strobe and phase))
            phase = not phase  # AHCT74 clocks on the inverted-strobe edge
        check(phase is initial_phase)

    # BUS_RUN also drives both AHCT74 active-low CLR inputs.
    for run_n, pwr_good in product((False, True), repeat=2):
        bus_run = run_n and pwr_good
        phase = True
        if not bus_run:
            phase = False
        check(phase is (run_n and pwr_good))
        if not bus_run:
            check(not (bus_run and phase))

    print(f"PASS: {checks} exhaustive Boolean assertions")
    print("Limits: equations only; no electrical/timing, KiCad ERC, PIO, or hardware validation")


if __name__ == "__main__":
    main()
