"""Builds outputs/dashboard.html (self-contained: images embedded as base64) from the run outputs."""
import base64, json, os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def b64(path):
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()


def main(out="outputs"):
    s = json.load(open(f"{out}/simulation_summary.json")); m = json.load(open(f"{out}/metrics.json"))
    e = json.load(open(f"{out}/eda_summary.json")); log = pd.read_csv(f"{out}/receiver_log.csv")
    # live-style monitor chart: receiver view with alarms
    fig, ax = plt.subplots(2, 1, figsize=(10, 4.6), sharex=True); x = pd.to_datetime(log.timestamp)
    ax[0].plot(x, log.temp_C, lw=0.5, color="#264653"); ax[0].set_ylabel("Temp (°C)")
    ax[1].plot(x, log.vibration_g, lw=0.5, color="#e76f51"); ax[1].set_ylabel("Vib (g)")
    a = log[log.rule_alarm == 1]
    for axis, c in zip(ax, ["temp_C", "vibration_g"]): axis.scatter(pd.to_datetime(a.timestamp), a[c], s=4, color="#d62828")
    ax[0].set_title("Receiver node view: decoded signals with raised alarms (red)"); plt.tight_layout()
    plt.savefig(f"{out}/figures/fig_receiver_view.png", dpi=120); plt.close()

    rows = "".join(f"<tr><td>{r.timestamp}</td><td>{r.can_id}</td><td>{r.temp_C:.1f}</td><td>{r.vibration_g:.3f}</td>"
                   f"<td>{r.rpm}</td><td>{r.status}</td><td>{r.display}</td></tr>" for r in a.head(15).itertuples())
    kpi = lambda k, v: f"<div class=k><b>{v}</b><span>{k}</span></div>"
    imgs = "".join(f"<img src='data:image/png;base64,{b64(f'{out}/figures/{n}.png')}'>" for n in
                   ["fig_receiver_view", "fig_timeseries", "fig_distributions", "fig_confusion", "fig_roc"])
    html = f"""<!doctype html><meta charset=utf-8><title>Vehicle Health Monitor</title>
<style>body{{font-family:Segoe UI,Arial;margin:24px;background:#f4f6f8;color:#222}}h1{{margin:0 0 4px}}
.k{{display:inline-block;background:#fff;border-radius:8px;padding:12px 18px;margin:6px;box-shadow:0 1px 3px #0002;text-align:center}}
.k b{{display:block;font-size:22px}}.k span{{font-size:12px;color:#666}}img{{max-width:100%;background:#fff;margin:8px 0;border-radius:8px}}
table{{border-collapse:collapse;background:#fff}}td,th{{padding:5px 10px;border:1px solid #ddd;font-size:13px}}th{{background:#264653;color:#fff}}</style>
<h1>Vehicle Health Monitoring System Using CAN</h1><p>Software twin run on {s['frames_sent']:,} frames</p>
{kpi('Frames sent', f"{s['frames_sent']:,}")}{kpi('Decoded', f"{s['frames_decoded']:,}")}
{kpi('CRC errors caught', s['crc_errors_detected'])}{kpi('Fault episodes detected', f"{s['episodes_detected']}/{s['fault_episodes']}")}
{kpi('Rule precision', s['rule_alarm']['precision'])}{kpi('Rule recall', s['rule_alarm']['recall'])}
{kpi('RF F1 (test)', m['random_forest']['f1'])}{kpi('IsolationForest F1', m['isolation_forest']['f1'])}
<h2>First alarms raised by the receiver</h2><table><tr><th>Time</th><th>CAN ID</th><th>Temp °C</th><th>Vib g</th><th>RPM</th><th>Status</th><th>7-seg</th></tr>{rows}</table>
<h2>Charts</h2>{imgs}"""
    open(f"{out}/dashboard.html", "w", encoding="utf-8").write(html)
    return f"{out}/dashboard.html"


if __name__ == "__main__":
    print(main())
