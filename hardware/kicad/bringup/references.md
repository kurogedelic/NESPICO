# Bring-up fixture reference notes

These primary-source references support the **candidate measurement fixture only**. They do not constitute electrical sign-off or approval to connect a live cartridge.

## Raspberry Pi Pico 2

- [Raspberry Pi Pico 2 Datasheet (RP-008299)](https://pip.raspberrypi.com/documents/RP-008299-DS), accessed 2026-10-12.
- Mechanical drawing (datasheet pp. 7–8): 51 × 21 mm module; header-row centers are 17.78 mm apart; 20 positions per row span 48.26 mm at 2.54 mm pitch. The fixture uses two 1×20 sockets at this row spacing.
- Pinout (datasheet Figure 2): GP26, GP27 and GP28 appear on the 40-pin header and are ADC0, ADC1 and ADC2 capable. GP29/ADC3 is used on the Pico 2 board to measure VSYS/3 and is not on the 40-pin header.
- Physical pin numbering (datasheet Figure 4): J1 local pad positions 1–20 map to physical pins 1–20 top-to-bottom; J2 local positions 1–20 map to physical pins 40–21 top-to-bottom. Thus J2.7/8/9/10 are physical pins 34/33/32/31: GP28/AGND/GP27/GP26. J5.1–4 are ADC2/AGND/ADC1/ADC0. This mapping is checked by `validate_bringup.py`.
- Electrical caveat (datasheet section 5.2): ADC-capable GPIO26–29 have a reverse diode to IOVDD; input voltage must not exceed approximately IOVDD + 0.3 V. Applying voltage while the RP2350 is unpowered can leak current into IOVDD. The fixture labels the ADC header for a conservative 0–3.3 V range and warns against driving it while unpowered; it adds no divider, clamp, or source-conditioning parts because the intended analog source is not defined.
- Power (datasheet section 3.1): VBUS is nominally 5 V when USB is present; 3V3 is the regulated output and Raspberry Pi recommends keeping external loads below 300 mA. This fixture uses VBUS only for the AHCT test buffer and does not supply cartridge power.

## 5 V transmit buffer candidate

- [Texas Instruments SNx4AHCT245 datasheet (SCLS233S)](https://www.ti.com/lit/ds/scls233p/scls233p.pdf), accessed 2026-10-12.
- SN74AHCT245 recommended VCC = 4.5–5.5 V; VIH(min) = 2.0 V; VIL(max) = 0.8 V; input range = 0–5.5 V. A 3.3 V Pico output therefore satisfies the documented input-high threshold under the stated supply conditions.
- Candidate function is fixed A→B. The datasheet's direction/OE function table requires OE low to enable. Pull-ups default TX_OE_N high (disabled) during reset/boot. Output contention/current and the full 5 V interface remain subject to measurement and datasheet review.

## 5 V receive buffer candidate

- [Texas Instruments SN74LVC245A datasheet (SCAS218X)](https://www.ti.com/lit/gpn/SN74LVC245A), accessed 2026-10-12.
- Recommended VCC = 1.65–3.6 V; at VCC = 2.7–3.6 V, VIH(min) = 2.0 V and the input range is specified to 5.5 V. The datasheet describes Ioff partial-power-down support and recommends pulling OE up to VCC for high-impedance behavior at power-up/down.
- Candidate function is fixed B→A at Pico 3.3 V. These device-level characteristics do not establish cartridge hot-plug, ESD, board-level power sequencing, or source-release timing safety.

## Board status

The separate KiCad files are a hand-assembled 8-bit buffer bring-up fixture, not the complete NESPICO 60-pin interface. It contains no cartridge connector, cartridge power switch, connector-side ESD network, address latches, CIRAM/audio/IRQ logic, or production/fabrication sign-off. Confirm exact orderable package variants, Pico socket height, native KiCad DRC, routing clearances, and physical assembly before any board order. Generated Gerber and Excellon files are explicitly marked as a review draft; no fabrication order has been placed.
