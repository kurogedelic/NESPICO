# Preliminary cartridge data-bus turnaround SPICE model

This is a **one-bit electrical-interface screening model**, not a cartridge interface design or sign-off. It makes output-enable relationships explicit before further schematic work.

## Topology considered

- RP2350 GPIO logic drives an SN74AHCT244-class 5 V buffer toward the cartridge.
- A separate SN74LVC244A-class 3.3 V buffer receives the cartridge-side 5 V data and drives the RP2350 GPIO.
- Both buffer groups are tri-state; separate active-low enables must be mutually exclusive, with break-before-make behavior.
- The cartridge is represented by a generic 5 V source behind an assumed 50 Ω output resistance. Its disable/release delay is swept rather than asserted as a NES specification.

This split-path topology is a **candidate for review**, not a selected/approved part implementation. No board pin numbers, connector symbol, cartridge 5 V power circuit, or physical connector footprint is included.

## Run

From the repository root:

```sh
python3 hardware/spice/run_turnaround.py
```

Requires ngspice. The script runs 35 transient cases and writes CSV/JSON/Markdown/SVG results plus three representative decks and logs under `hardware/spice/results/`.

## Model inputs and source basis

- TI SN74AHCT244 datasheet, SCLS228O (revised July 2024): 4.5–5.5 V supply, VIH(min)=2.0 V, VIL(max)=0.8 V, 3.3 V input to 5 V output use, active-low `/OE`, max 13 ns output-enable delay with 50 pF load, VOH(min)=3.8 V and VOL(max)=0.44 V at 8 mA. The 55 Ω AHCT low-side resistor here is the linear equivalent `0.44 V / 8 mA`; it is **not** a transistor model and is extrapolated only to expose possible contention.
- TI application guidance for the AHCT244 recommends output loads not exceed 25 mA per output or 50 mA total for the part. The graph's 25 mA line is only an AHCT244 comparison; it is **not** a permissible-current limit for the LVC244A or RP2350.
- TI SN74LVC244A datasheet, SCAS414AG (revised June 2026): 1.65–3.6 V supply, 0–5.5 V input range, `/OE` 3-state outputs, `Ioff` partial-power-down behavior, and 8 ns maximum output-disable delay at 3.3 V with the specified 50 pF load. These input/power-off limits are conditional on the datasheet conditions; they do not make an unspecified module/cartridge hot-plug safe.
- Cartridge output release delay (0, 10, 20, 30, and 50 ns): scenario values only. A real cartridge's active-driver behavior depends on its logic, address/strobe timing, and state; it has not been measured.
- Cartridge-side output resistance (50 Ω), LVC output resistance (50 Ω), RP2350 GPIO equivalent resistance (50 Ω placeholder), and 50 pF node loads are screening assumptions. The RP2350 resistor is not inferred from a GPIO datasheet guarantee.

## Interpretation

The generated summary table requires **both modeled source branches to remain below a 1 mA overlap-detection threshold**; the separate 25 mA line is not used as the MCU-side limit. At the sampled points, the first tested no-overlap guard is 8 ns for assumed cartridge releases of 0–20 ns, 20 ns for 30 ns, and 40 ns for 50 ns. In the 20 ns scenario the AHCT's assumed 13 ns enable delay leaves less than 8 ns required from the cartridge-side equation, while the separate LVC/RP direction handoff still requires the 8 ns tested guard.

The sweep is intended to reveal modeled overlap, not select a real guard time. Maximum modeled branches were approximately 47.6 mA cartridge-side and 32.9 mA MCU-side when drivers overlapped. These are switch/resistor-model results, **not predictions of actual silicon current**.

A low modeled branch current only means the idealized switches were not simultaneously conducting in that case. The simulation omits nonlinear device output curves, input thresholds, line inductance, connector/contact variation, ESD, overshoot, ringing, crosstalk, supply sequencing, metastability, actual RP2350 pad behavior, and actual cartridge timing. It cannot establish safe operation or hardware suitability.

## Sources

- [TI SN74AHCT244 datasheet](https://www.ti.com/lit/ds/scls228m/scls228m.pdf)
- [TI SN74LVC244A datasheet](https://www.ti.com/lit/ds/symlink/sn74lvc244a.pdf)
- [RP2350 datasheet](https://pip.raspberrypi.com/documents/RP-008373-DS-rp2350-datasheet.pdf) (module-specific GPIO pad class and board routing remain unverified)
- Project-level connector constraints: [`docs/famicom-60pin-signal-register.md`](../../docs/famicom-60pin-signal-register.md)
