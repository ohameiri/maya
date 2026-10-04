# Analysis scripts

These scripts produce the numbers and plots in [`docs/design_review.md`](../docs/design_review.md). The plots are written to [`docs/review/`](../docs/review).

| Script | Purpose |
|---|---|
| `ngs.py` | Minimal ctypes wrapper around the system `libngspice.so.0` (shared API). PySpice does not work with ngspice 42. |
| `pwr.py` | Power-path SPICE model: USB host and cable, B5819W, AP7361C (soft-start, current limit, fold-back, dropout), LM66100 ideal diodes, DC-bias-derated MLCCs. |
| `c1.py` | C1 USB plug-in power-up and C3 inrush: writes `c1_powerup.png` and `c3_inrush.png`. |
| `c2.py` | C2 LoRa +22 dBm TX together with a Wi-Fi TX burst: writes `c2_tx_droop.png`. |
| `c4.py` | C4 switching between the supply sources: writes `c4_switchover.png`. |
| `rfsim.py` | Nodal (MNA) model of both RF networks, built from the board netlist, with parasitics for the 0402 parts. |
| `rfplot.py` | D1 RF response of both bands: writes `d1_rf_response.png`. |
| `rftopo.py` | Compares our RF networks with Semtech's reference design as labelled graphs. Run it as `python3 rftopo.py <reference .kicad_pcb> ../lr2021_esp32s3.kicad_pcb`. |

## Requirements
- Python 3 with numpy, matplotlib and networkx.
- ngspice 42 as a shared library (`libngspice.so.0`, from the Debian/Ubuntu `libngspice0` package).
- KiCad 9's `pcbnew` module for `/usr/bin/python3`. `rfsim.py` and `rftopo.py` read the board through it in a subprocess.

The reference board for `rftopo.py` is the KiCad port of Semtech's e788v01a in [busterbn/lr2021_kicad](https://github.com/busterbn/lr2021_kicad).
