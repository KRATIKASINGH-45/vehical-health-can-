"""End-to-end run: TransmitterNode -> VirtualCanBus (loss + corruption) -> ReceiverNode.

  python -m src.simulate                    # full 15,000-frame run, writes outputs/receiver_log.csv
  python -m src.simulate --live --rows 120  # console demo with 7-segment display, ~20 frames/s
"""
import argparse, json, pickle, time, os
import numpy as np, pandas as pd
from .virtual_can_bus import VirtualCanBus
from .transmitter_node import TransmitterNode
from .receiver_node import ReceiverNode
from . import seven_segment


def load_model(path="outputs/model_rf.pkl"):
    if os.path.exists(path):
        with open(path, "rb") as fh:
            return pickle.load(fh)
    return None


def episodes(flag):
    f = np.asarray(flag); starts = np.where((f == 1) & (np.r_[0, f[:-1]] == 0))[0]
    ends = np.where((f == 1) & (np.r_[f[1:], 0] == 0))[0]
    return list(zip(starts, ends))


def evaluate(log_df, truth_df):
    m = truth_df.merge(log_df[["timestamp", "rule_alarm", "ml_alarm"]], on="timestamp", how="left")
    received = m.rule_alarm.notna()
    out = {"frames_received_matched": int(received.sum())}
    for col in ("rule_alarm", "ml_alarm"):
        r = m[received]; y, p = r.alarm_flag.values, r[col].astype(int).values
        tp = int(((y == 1) & (p == 1)).sum()); fp = int(((y == 0) & (p == 1)).sum()); fn = int(((y == 1) & (p == 0)).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0; rec = tp / (tp + fn) if tp + fn else 0.0
        out[col] = dict(tp=tp, fp=fp, fn=fn, precision=round(prec, 4), recall=round(rec, 4),
                        f1=round(2 * prec * rec / (prec + rec), 4) if prec + rec else 0.0)
    # episode-level detection and latency (seconds = rows, 1 Hz)
    eps, hit, lat = episodes(truth_df.alarm_flag.values), 0, []
    alarm_by_ts = dict(zip(log_df.timestamp, log_df.rule_alarm))
    for s, e in eps:
        for k in range(s, e + 1):
            if alarm_by_ts.get(truth_df.timestamp.iloc[k], 0) == 1:
                hit += 1; lat.append(k - s); break
    out["fault_episodes"] = len(eps); out["episodes_detected"] = hit
    out["mean_detection_delay_s"] = round(float(np.mean(lat)), 2) if lat else None
    return out


def run(rows=None, loss=0.005, corrupt=0.002, seed=7, data="data/dataset.csv", out="outputs"):
    os.makedirs(out, exist_ok=True)
    bus = VirtualCanBus(loss_rate=loss, corrupt_rate=corrupt, seed=seed)
    tx = TransmitterNode(bus, data); n = tx.run(rows)
    rx = ReceiverNode(bus, model=load_model(f"{out}/model_rf.pkl")); rx.run()
    log = pd.DataFrame(rx.log); log.to_csv(f"{out}/receiver_log.csv", index=False)
    truth = tx.df.head(n)
    s = dict(frames_sent=bus.sent, frames_dropped_on_bus=bus.dropped, frames_corrupted_on_bus=bus.corrupted,
             frames_decoded=len(log), crc_errors_detected=rx.crc_errors, missing_frames_via_sequence=rx.missing_frames,
             crc_detection_rate=round(rx.crc_errors / bus.corrupted, 4) if bus.corrupted else None,
             loss_rate=loss, corrupt_rate=corrupt)
    s.update(evaluate(log, truth))
    with open(f"{out}/simulation_summary.json", "w") as fh:
        json.dump(s, fh, indent=2)
    return s, log


def live(rows, speed):
    bus = VirtualCanBus(); tx = TransmitterNode(bus); rx = ReceiverNode(bus, model=load_model())
    first = int(tx.df.index[tx.df.alarm_flag == 1][0])
    start = max(0, first - 20)   # start shortly before the first fault so a short demo shows an alarm
    df = tx.df.iloc[start:start + rows]; tx.df = df; tx.run()
    while len(bus):
        r = rx.poll()
        if r is None: continue
        flag = "  <<< ALARM" if r["rule_alarm"] else ""
        print(f"{r['timestamp']} id={r['can_id']} T={r['temp_C']:6.1f}C V={r['vibration_g']:.3f}g "
              f"RPM={r['rpm']:4d} [{r['display']}] {r['status']}{flag}")
        if r["rule_alarm"] and rx.log[-2:-1] and not rx.log[-2]["rule_alarm"]:
            print(seven_segment.render(r["display"]))
        time.sleep(1.0 / speed)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true"); ap.add_argument("--rows", type=int, default=None)
    ap.add_argument("--speed", type=float, default=20)
    ap.add_argument("--loss", type=float, default=0.005); ap.add_argument("--corrupt", type=float, default=0.002)
    a = ap.parse_args()
    if a.live:
        live(a.rows or 120, a.speed)
    else:
        summary, _ = run(a.rows, a.loss, a.corrupt); print(json.dumps(summary, indent=2))
