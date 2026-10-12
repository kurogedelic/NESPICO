# NESPICO

**USB Famicom cartridge reader + live-cartridge console experiment** using a low-cost YD-RP2350A Zero and 74-series logic. No FPGA, HDMI shield, or wireless module.

This repository currently contains a **hardware-independent, deterministic timing model** and GitHub Actions tests. It is a feasibility testbed, **not** a working NES emulator or verified electronics design.

## What runs now

- CPU and PPU independently scheduled in NTSC timing; representative background/sprite fetches
- Synthetic 74AHCT574 address latches and independent data-bus transceivers
- Per-transaction bus deadline checks and CPU/PPU overlap accounting
- NROM-like cartridge model with CHR-ROM/CHR-RAM and disconnected open-bus approximation
- Parameterized *partial* MMC3 A12 filter / IRQ model
- RESET preserves 2 KiB CPU RAM; power-cycle test clears it
- Rough, explicit USB bandwidth assumption (not a USB driver benchmark)
- GitHub Actions: Python 3.10 and 3.12, tests + full-frame stress + expected-failure test

```bash
python -m unittest discover -s tests -v
python -m nespico.cli --scanlines 262
python -m nespico.cli --pio-mhz 20 --settle-ns 160 --scanlines 1   # intentionally fails
```

**Interpretation:** A successful simulated timing run means only that independently prepared address/data transactions fit assumed bus windows. **It does not prove** that the RP2350 can run a cycle-exact CPU+PPU while feeding the PIO FIFOs, nor that the GPIO assignment, 5V interface, cartridge mapping, physical timing, USB streaming or World 9 exploit works.

Architecture, omissions and next hardware experiments: [docs/architecture.md](docs/architecture.md).

References: [NESdev cartridge connector](https://www.nesdev.org/wiki/Cartridge_connector), [NESdev PPU rendering](https://www.nesdev.org/wiki/PPU_rendering), [NESdev MMC3](https://www.nesdev.org/wiki/MMC3), [RP2350 documentation](https://www.raspberrypi.com/documentation/microcontrollers/silicon.html).
