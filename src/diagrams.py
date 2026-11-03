"""Draws docs/architecture.png (block diagram) and docs/dfd_level0.png (Data Flow Diagram level 0)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle


def box(ax, x, y, w, h, text, fc="#e9f2f9", ec="#264653", fs=8.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def arrow(ax, p, q, text="", dy=0.12):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="->", lw=1.3, color="#264653"))
    if text: ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + dy, text, ha="center", fontsize=7.5, color="#444")


def main(out="docs"):
    os.makedirs(out, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 4.6)); ax.set_xlim(0, 11); ax.set_ylim(0, 4.6); ax.axis("off")
    ax.text(2.1, 4.35, "TRANSMITTER NODE (STM32F103)", ha="center", fontsize=9, weight="bold")
    ax.text(8.9, 4.35, "RECEIVER NODE (STM32F103)", ha="center", fontsize=9, weight="bold")
    for i, t in enumerate(["DHT11\ntemperature", "Vibration sensor\n(analog / ADC)", "RPM sensor\n(Hall / IR, EXTI)"]):
        box(ax, 0.1, 3.0 - i * 1.15, 1.6, 0.85, t, fc="#fff3e0"); arrow(ax, (1.7, 3.42 - i * 1.15), (2.4, 2.55 - 0.0), dy=0)
    box(ax, 2.4, 1.5, 1.7, 1.9, "STM32 MCU\nsample 1 Hz\npack 8-byte frame\nCRC-8 + sequence", fc="#e9f2f9")
    box(ax, 4.5, 1.7, 1.2, 1.5, "bxCAN\nMCP2551 /\nTJA1050\ntransceiver", fc="#dff6dd"); arrow(ax, (4.1, 2.45), (4.5, 2.45))
    ax.plot([5.7, 6.9], [2.8, 2.8], color="#2a9d8f", lw=3); ax.plot([5.7, 6.9], [2.1, 2.1], color="#e76f51", lw=3)
    ax.text(6.3, 3.0, "CAN_H", ha="center", fontsize=8, color="#2a9d8f"); ax.text(6.3, 1.75, "CAN_L", ha="center", fontsize=8, color="#e76f51")
    ax.text(6.3, 2.45, "500 kbit/s\n120 Ω termination", ha="center", fontsize=7.5)
    box(ax, 6.9, 1.7, 1.2, 1.5, "bxCAN\ntransceiver\nID filter\n0x101-0x103", fc="#dff6dd")
    box(ax, 8.4, 1.5, 1.7, 1.9, "STM32 MCU\nCRC check, decode\nrule engine\nfault_code", fc="#e9f2f9"); arrow(ax, (8.1, 2.45), (8.4, 2.45))
    box(ax, 8.4, 0.2, 1.1, 0.8, "7-segment\ndisplay", fc="#fff3e0"); box(ax, 9.6, 0.2, 1.1, 0.8, "Buzzer +\nLED", fc="#fde2e4")
    arrow(ax, (9.0, 1.5), (8.95, 1.0), dy=0); arrow(ax, (9.7, 1.5), (10.1, 1.0), dy=0)
    box(ax, 4.6, 0.1, 3.4, 0.9, "Optional: Raspberry Pi / PC gateway\n(Python: logging, ML, dashboard)", fc="#f3e8ff"); arrow(ax, (8.4, 1.8), (8.0, 0.8), "UART / MQTT", dy=0.08)
    plt.tight_layout(); plt.savefig(f"{out}/architecture.png", dpi=150); plt.close()

    fig, ax = plt.subplots(figsize=(10, 3.8)); ax.set_xlim(0, 10); ax.set_ylim(0, 3.8); ax.axis("off")
    ax.add_patch(Circle((5, 1.9), 1.2, fc="#e9f2f9", ec="#264653", lw=1.5))
    ax.text(5, 1.9, "0\nVehicle Health\nMonitoring\nSystem (CAN)", ha="center", va="center", fontsize=9, weight="bold")
    box(ax, 0.2, 2.6, 2.0, 0.8, "Vehicle sensors\n(temp, vibration, rpm)", fc="#fff3e0"); box(ax, 0.2, 0.4, 2.0, 0.8, "Dataset\n(dataset.csv, 15,000 rows)", fc="#fff3e0")
    box(ax, 7.8, 2.6, 2.0, 0.8, "Driver / Operator", fc="#fde2e4"); box(ax, 7.8, 0.4, 2.0, 0.8, "Maintenance engineer\n(dashboard, logs)", fc="#fde2e4")
    arrow(ax, (2.2, 3.0), (4.0, 2.5), "sensor readings", 0.15); arrow(ax, (2.2, 0.8), (4.0, 1.4), "replayed frames", -0.25)
    arrow(ax, (6.0, 2.5), (7.8, 3.0), "alarm + 7-seg code", 0.15); arrow(ax, (6.0, 1.4), (7.8, 0.8), "reports, metrics", -0.25)
    ax.set_title("Data Flow Diagram - Level 0", fontsize=10)
    plt.tight_layout(); plt.savefig(f"{out}/dfd_level0.png", dpi=150); plt.close()


if __name__ == "__main__":
    main()
