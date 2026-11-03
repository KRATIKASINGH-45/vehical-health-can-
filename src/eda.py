"""Exploratory data analysis: writes 6 figures + outputs/eda_summary.json."""
import json, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NAMES = {0: "Normal", 101: "Overheating", 102: "Abnormal vibration", 103: "Overheat + vibration"}
COL = {0: "#6c757d", 101: "#d62828", 102: "#f77f00", 103: "#7b2cbf"}


def main(path="data/dataset.csv", out="outputs"):
    os.makedirs(f"{out}/figures", exist_ok=True)
    df = pd.read_csv(path, dtype={"node_id": str}, parse_dates=["timestamp"])
    s = {}
    s["rows"], s["columns"] = df.shape
    s["missing_values"] = int(df.isna().sum().sum())
    s["duplicate_timestamps"] = int(df.timestamp.duplicated().sum())
    s["duration_hours"] = round((df.timestamp.iloc[-1] - df.timestamp.iloc[0]).total_seconds() / 3600, 2)
    s["fault_rows"] = int(df.alarm_flag.sum()); s["fault_pct"] = round(100 * df.alarm_flag.mean(), 2)
    s["fault_code_counts"] = {str(k): int(v) for k, v in df.fault_code.value_counts().items()}
    s["idle_pct"] = round(100 * (df.rpm < 1000).mean(), 1)
    s["describe"] = df[["temp_C", "vibration_g", "rpm"]].describe().round(3).to_dict()
    s["by_alarm"] = df.groupby("alarm_flag")[["temp_C", "vibration_g", "rpm"]].mean().round(3).to_dict()
    s["node_counts"] = df.node_id.value_counts().to_dict()
    # fault episodes
    ep = (df.alarm_flag.diff().fillna(df.alarm_flag.iloc[0]) == 1).cumsum() * df.alarm_flag
    s["fault_episodes"] = int(ep.max()); s["mean_episode_len_s"] = round(float(df[df.alarm_flag == 1].groupby(ep).size().mean()), 1)

    # Fig 1: temperature time series with faults highlighted
    x = df.timestamp
    fig, ax = plt.subplots(3, 1, figsize=(10, 6.2), sharex=True)
    for a, c, lab in zip(ax, ["temp_C", "vibration_g", "rpm"], ["Temperature (°C)", "Vibration (g)", "Engine speed (rpm)"]):
        a.plot(x, df[c], lw=0.5, color="#264653")
        f = df[df.alarm_flag == 1]; a.scatter(f.timestamp, f[c], s=3, color="#d62828", label="fault rows", zorder=3)
        a.set_ylabel(lab, fontsize=8)
    ax[0].axhline(105, color="#d62828", ls="--", lw=0.8); ax[1].axhline(0.8, color="#d62828", ls="--", lw=0.8)
    ax[0].legend(loc="upper left", fontsize=7); ax[0].set_title("CAN signals over the 4.2-hour drive log (faults in red)")
    ax[2].set_xlabel("Time"); plt.tight_layout(); plt.savefig(f"{out}/figures/fig_timeseries.png", dpi=130); plt.close()

    # Fig 2: distributions normal vs fault
    fig, ax = plt.subplots(1, 3, figsize=(10, 3.2))
    for a, c, lab in zip(ax, ["temp_C", "vibration_g", "rpm"], ["Temperature (°C)", "Vibration (g)", "Engine speed (rpm)"]):
        a.hist(df[df.alarm_flag == 0][c], bins=50, alpha=0.7, color="#2a9d8f", label="Normal", density=True)
        a.hist(df[df.alarm_flag == 1][c], bins=30, alpha=0.7, color="#d62828", label="Fault", density=True)
        a.set_xlabel(lab); a.set_yticks([])
    ax[0].legend(fontsize=8); fig.suptitle("Signal distributions: normal vs fault", fontsize=10)
    plt.tight_layout(); plt.savefig(f"{out}/figures/fig_distributions.png", dpi=130); plt.close()

    # Fig 3: rpm vs vibration scatter coloured by fault code
    plt.figure(figsize=(6.2, 4.2))
    for code, g in df.groupby("fault_code"):
        plt.scatter(g.rpm, g.vibration_g, s=4 if code == 0 else 14, color=COL[code], label=NAMES[code], alpha=0.5 if code == 0 else 0.9)
    plt.xlabel("Engine speed (rpm)"); plt.ylabel("Vibration (g)"); plt.legend(markerscale=2, fontsize=8)
    plt.title("Vibration vs engine speed"); plt.tight_layout(); plt.savefig(f"{out}/figures/fig_scatter.png", dpi=130); plt.close()

    # Fig 4: correlation heat-map
    corr = df[["temp_C", "vibration_g", "rpm", "fault_code", "alarm_flag"]].corr()
    plt.figure(figsize=(5.2, 4.2)); plt.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1); plt.colorbar()
    plt.xticks(range(5), corr.columns, rotation=40, ha="right", fontsize=8); plt.yticks(range(5), corr.columns, fontsize=8)
    for (i, j), v in np.ndenumerate(corr.values): plt.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8)
    plt.title("Correlation matrix"); plt.tight_layout(); plt.savefig(f"{out}/figures/fig_correlation.png", dpi=130); plt.close()

    # Fig 5: class balance
    vc = df.fault_code.value_counts().sort_index()
    plt.figure(figsize=(5.4, 3.4)); b = plt.bar([NAMES[k] for k in vc.index], vc.values, color=[COL[k] for k in vc.index])
    plt.yscale("log"); plt.ylabel("Rows (log scale)"); plt.xticks(rotation=15, fontsize=8)
    for r, v in zip(b, vc.values): plt.text(r.get_x() + r.get_width() / 2, v, str(v), ha="center", va="bottom", fontsize=8)
    plt.title("Class balance (%.2f%% faults)" % s["fault_pct"]); plt.tight_layout()
    plt.savefig(f"{out}/figures/fig_class_balance.png", dpi=130); plt.close()

    # Fig 6: zoom on one fault episode
    first = df.index[df.alarm_flag == 1][0]; lo, hi = max(0, first - 40), first + 80
    z = df.iloc[lo:hi]; fig, ax = plt.subplots(2, 1, figsize=(7.5, 4.2), sharex=True)
    ax[0].plot(z.timestamp, z.temp_C, color="#264653"); ax[0].axhline(105, color="#d62828", ls="--", lw=0.8); ax[0].set_ylabel("Temp (°C)")
    ax[1].plot(z.timestamp, z.vibration_g, color="#e76f51"); ax[1].axhline(0.8, color="#d62828", ls="--", lw=0.8); ax[1].set_ylabel("Vib (g)")
    for a in ax: a.axvspan(z[z.alarm_flag == 1].timestamp.min(), z[z.alarm_flag == 1].timestamp.max(), color="#d62828", alpha=0.12)
    ax[0].set_title("Zoom: first fault episode (shaded = alarm_flag 1)"); plt.xticks(rotation=20, fontsize=7)
    plt.tight_layout(); plt.savefig(f"{out}/figures/fig_episode_zoom.png", dpi=130); plt.close()

    with open(f"{out}/eda_summary.json", "w") as fh:
        json.dump(s, fh, indent=2)
    return s


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
