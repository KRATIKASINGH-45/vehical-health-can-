"""Receiver node (software twin of the STM32 receiver).

For every frame: CRC check -> decode -> sequence-gap check -> rule engine (+ optional ML model)
-> 4-character 7-segment text -> log row.  Uses only past samples, so it is causal like the firmware.
"""
from collections import deque
import numpy as np
import pandas as pd
from .can_protocol import decode, VALID_IDS
from .fault_detection import rule_fault_code, FAULT_NAMES, FEATURES
from . import seven_segment


class ReceiverNode:
    def __init__(self, bus, model=None, ml_threshold=0.5):
        self.bus, self.model, self.ml_threshold = bus, model, ml_threshold
        self.log = []
        self.crc_errors = self.unknown_ids = self.missing_frames = 0
        self._last_seq = {}
        self._temp, self._vib, self._rpm = deque(maxlen=5), deque(maxlen=5), deque(maxlen=5)

    # --- features identical to fault_detection.add_window_features (causal) ---
    def _features(self, t, v, r):
        self._temp.append(t); self._vib.append(v); self._rpm.append(r)
        tt, vv, rr = np.array(self._temp), np.array(self._vib), np.array(self._rpm)
        slope = (tt[-1] - tt[0]) / 4 if len(tt) == 5 else 0.0
        vstd = vv.std(ddof=1) if len(vv) >= 2 else 0.0
        rstd = rr.std(ddof=1) if len(rr) >= 2 else 0.0
        return [t, v, r, tt.mean(), slope, vv.mean(), vstd, rstd]

    def display_text(self, temp_c, code):
        """Normal: 3-digit temperature + 'H' marker. Fault: 'E' + code (E101 / E102 / E103)."""
        return f"E{code}" if code else f"{int(round(temp_c)):03d}H"

    def poll(self):
        frame = self.bus.receive()
        if frame is None:
            return None
        if frame.can_id not in VALID_IDS:
            self.unknown_ids += 1
            return None
        try:
            t, v, r, seq = decode(frame)
        except ValueError:
            self.crc_errors += 1
            return None
        if frame.can_id in self._last_seq:
            self.missing_frames += (seq - self._last_seq[frame.can_id] - 1) & 0xFF
        self._last_seq[frame.can_id] = seq

        feats = self._features(t, v, r)
        rule_code = rule_fault_code(t, v)
        ml_alarm = 0
        if self.model is not None:
            ml_alarm = int(self.model.predict_proba(pd.DataFrame([feats], columns=FEATURES))[0][1] >= self.ml_threshold)
        text = self.display_text(t, rule_code)
        row = dict(timestamp=frame.timestamp, can_id=hex(frame.can_id), temp_C=t, vibration_g=v, rpm=r,
                   rule_fault_code=rule_code, rule_alarm=int(rule_code != 0), ml_alarm=ml_alarm,
                   status=FAULT_NAMES[rule_code], display=text)
        self.log.append(row)
        return row

    def run(self):
        while len(self.bus):
            self.poll()
        return self.log
