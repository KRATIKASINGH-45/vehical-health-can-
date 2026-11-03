# Software Requirements Specification (summary)

## Functional requirements
| ID | Requirement |
|----|-------------|
| FR1 | Transmitter shall sample temperature, vibration and rpm once per second and send one 8-byte CAN 2.0A frame (IDs 0x101-0x103). |
| FR2 | Each frame shall carry a rolling sequence counter and a CRC-8 over bytes 0-6. |
| FR3 | Receiver shall reject frames with an invalid CRC or unknown ID and count them. |
| FR4 | Receiver shall estimate lost frames from sequence-counter gaps per node. |
| FR5 | Receiver shall raise fault 101 (temp >= 105 C), 102 (vibration >= 0.80 g) or 103 (both) and set alarm_flag. |
| FR6 | Receiver shall show the temperature (normal) or `E101/E102/E103` (fault) on a 4-digit 7-segment display and drive a buzzer + LED. |
| FR7 | The Python layer shall log every decoded frame to CSV and produce an HTML dashboard. |
| FR8 | The Python layer shall train and evaluate a supervised and an unsupervised detector on a chronological split. |

## Non-functional requirements
| ID | Requirement |
|----|-------------|
| NFR1 | Fault-to-alarm delay <= 1 s (one sampling period). |
| NFR2 | Full 15,000-frame simulation completes in under 60 s on a laptop. |
| NFR3 | `python run_all.py` reproduces every number in the report with fixed random seeds. |
| NFR4 | No credentials or personal data in the code or dataset. |

## Constraints
Classic CAN 2.0A, 500 kbit/s; 8-byte payload; DHT11 reads 0-50 C only (see README, "Hardware note"); dataset is synthetic.
