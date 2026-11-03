"""Robustness sweep: how do detection and link-integrity metrics change as the CAN bus gets worse?
Writes outputs/robustness.csv (one row per loss/corruption setting)."""
import pandas as pd
from .virtual_can_bus import VirtualCanBus
from .transmitter_node import TransmitterNode
from .receiver_node import ReceiverNode
from .simulate import evaluate

SETTINGS = [(0.0, 0.0), (0.005, 0.002), (0.02, 0.01), (0.05, 0.02), (0.10, 0.05)]


def main(data="data/dataset.csv", out="outputs"):
    rows = []
    for loss, cor in SETTINGS:
        bus = VirtualCanBus(loss_rate=loss, corrupt_rate=cor, seed=11)
        tx = TransmitterNode(bus, data); tx.run(); rx = ReceiverNode(bus); rx.run()
        ev = evaluate(pd.DataFrame(rx.log), tx.df)
        rows.append(dict(loss_pct=100 * loss, corrupt_pct=100 * cor, frames_sent=bus.sent, decoded=len(rx.log),
                         corrupted_on_bus=bus.corrupted, crc_rejected=rx.crc_errors, missing_by_seq=rx.missing_frames,
                         episodes_detected=f"{ev['episodes_detected']}/{ev['fault_episodes']}",
                         mean_delay_s=ev["mean_detection_delay_s"], rule_precision=ev["rule_alarm"]["precision"],
                         rule_recall=ev["rule_alarm"]["recall"]))
    df = pd.DataFrame(rows); df.to_csv(f"{out}/robustness.csv", index=False); return df


if __name__ == "__main__":
    print(main().to_string(index=False))
