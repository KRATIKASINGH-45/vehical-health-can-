# Vehicle Health Monitoring System Using CAN

HCLTech Career Shaper Programme - Project No. 8 (Embedded IoT) - Learner: Kratika Singh, Roll No. 2300320310106, ECE, ABES Engineering College

A CAN-bus vehicle health monitor. Sensor nodes send temperature, vibration and engine-speed frames; a receiver node
validates them (CRC-8 + sequence counter), detects **overheating (101)**, **abnormal vibration (102)** or **both (103)**,
and shows the code on a 7-segment display. This repository contains:

* a **fully running software twin** in Python (transmitter node -> virtual CAN bus with loss/corruption -> receiver node),
* EDA, ML detectors (Random Forest, Isolation Forest) and an HTML dashboard,
* **reference STM32 firmware** for the real transmitter and receiver (`firmware/`) - *not bench-tested here*,
* docs: problem statement, SRS, architecture/DFD diagrams, BOM, test report, and the project synopsis.

## Quick start (Python 3.10+)
```bash
pip install -r requirements.txt
python run_all.py            # EDA -> training -> CAN simulation -> dashboard -> robustness sweep -> 17 unit tests (about 30 s)
```
Then open `outputs/dashboard.html` in a browser. Individual steps:

| Command | What it does |
|---|---|
| `python -m src.eda` | 6 EDA figures + `outputs/eda_summary.json` |
| `python -m src.train_model` | trains/evaluates detectors -> `outputs/metrics.json`, `model_rf.pkl` |
| `python -m src.simulate` | full 15,000-frame CAN run (0.5% frame loss, 0.2% corruption) -> `outputs/receiver_log.csv`, `simulation_summary.json` |
| `python -m src.simulate --live --rows 60 --speed 20` | console demo with the 7-segment display, starts just before the first fault |
| `python -m src.robustness` | sweeps bus loss/corruption (0-10% / 0-5%) -> `outputs/robustness.csv` |
| `python -m src.dashboard` | rebuilds `outputs/dashboard.html` |
| `python -m unittest discover -s tests -v` | 17 unit/integration tests |
| `python data/generate_can_dataset.py` | regenerates the synthetic dataset (seed 42) |

## Folder layout
```
data/        dataset.csv (15,000 rows), data_dictionary.csv, generate_can_dataset.py
src/         can_protocol, virtual_can_bus, transmitter_node, receiver_node, fault_detection,
             seven_segment, eda, train_model, simulate, dashboard, diagrams
firmware/    stm32_transmitter/main.c, stm32_receiver/main.c   (STM32CubeIDE + HAL, reference code)
tests/       test_project.py
docs/        problem_statement.md, SRS.md, BOM.md, TEST_REPORT.md, architecture.png, dfd_level0.png
outputs/     figures, metrics, logs, dashboard (re-created by run_all.py)
```

## CAN frame (8 bytes, ID 0x101 engine / 0x102 transmission / 0x103 chassis, 500 kbit/s)
`[temp int16 x0.1 C][vibration uint16 mg][rpm uint16][seq uint8][CRC-8 poly 0x07]`

## Results (from `outputs/`, seed-fixed)
See `outputs/metrics.json` and `outputs/simulation_summary.json`. Read them with the caveats below.

## Honest limitations
1. **Synthetic data.** `dataset.csv` is generated, not recorded from a vehicle. Labels are *defined* by the thresholds
   (105 C, 0.80 g), so the rule engine and the supervised Random Forest score ~100% by construction. The informative
   numbers are the unsupervised Isolation Forest (never sees labels), the CRC/sequence-counter results, and the end-to-end tests.
2. **Early-warning model is weak** (precision ~0.10) - reported honestly in `metrics.json`; it needs real data.
3. **Firmware is untested on hardware.** It mirrors the Python twin line by line but must be compiled, calibrated and verified on a board.
4. **Hardware note - DHT11 range.** The DHT11 measures 0-50 C, so it cannot read coolant at 85-125 C. On a bench rig use it as an
   enclosure/ambient sensor with a scaled mapping, or swap in a thermocouple (MAX6675) / NTC probe for real coolant temperature.

## Ethics
Vehicle diagnostic data can be proprietary; follow OBD-II (SAE J1979 / ISO 15031) rules and the vehicle maker's terms before logging a real car.
This project uses only synthetic data and stores no personal data (DPDP Act 2023). Disclose the AI tool used to generate the dataset and code.
