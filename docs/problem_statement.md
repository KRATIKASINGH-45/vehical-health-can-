# Problem Statement (5W1H)

**Who** - drivers and fleet / workshop maintenance engineers.
**What** - engine overheating and abnormal vibration develop quickly and are noticed late, when a warning light or a breakdown is the first sign.
**When / where** - during normal driving (60-100 km/h) and idling, on any vehicle whose sensors are linked over a CAN bus.
**Why it matters** - an unnoticed overheating event can cause engine damage; excess vibration signals mechanical wear. Early, automatic detection reduces repair cost and risk.
**How** - sensor nodes publish temperature, vibration and rpm as 8-byte CAN frames at 1 Hz; a receiver node verifies each frame (CRC, sequence), applies threshold rules, shows a fault code on a 7-segment display and sounds a buzzer. A Python layer logs the data, runs machine-learning detectors and builds a dashboard.

**Success metrics** - (1) every fault episode in the log is detected with no more than 1 s delay, (2) 100% of corrupted frames are rejected by the CRC, (3) lost frames are counted from the sequence counter, (4) a label-free detector (Isolation Forest) flags faults without using `alarm_flag`.
