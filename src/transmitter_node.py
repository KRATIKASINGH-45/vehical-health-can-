"""Transmitter node (software twin of the STM32 sender): turns sensor readings into CAN frames."""
import pandas as pd
from .can_protocol import encode


class TransmitterNode:
    def __init__(self, bus, dataset_path="data/dataset.csv"):
        self.bus = bus
        self.df = pd.read_csv(dataset_path, dtype={"node_id": str})
        self._seq = {}

    def run(self, limit=None):
        rows = self.df if limit is None else self.df.head(limit)
        for r in rows.itertuples(index=False):
            can_id = int(r.node_id, 16)
            seq = self._seq.get(can_id, 0)
            self.bus.send(encode(can_id, r.temp_C, r.vibration_g, r.rpm, seq, r.timestamp))
            self._seq[can_id] = (seq + 1) & 0xFF
        return len(rows)
