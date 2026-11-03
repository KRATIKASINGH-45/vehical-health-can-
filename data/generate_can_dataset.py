"""
Synthetic CAN-bus dataset generator for: Vehicle Health Monitoring System Using CAN
Schema (from Project_Brief.docx):
  timestamp, node_id, temp_C, vibration_g, rpm, fault_code, alarm_flag
Run:  python generate_can_dataset.py
"""
import numpy as np, pandas as pd

SEED, N = 42, 15000
rng = np.random.default_rng(SEED)

# ---------- 1. Drive-cycle state machine (1 reading / second) ----------
# states: idle, accel, cruise (60-100 km/h), decel
speed = np.zeros(N)           # internal only, NOT written to CSV
state = np.empty(N, dtype=object)
i, v = 0, 0.0
seg = [("idle", int(rng.integers(120, 240)))]
while i < N:
    if not seg:
        seg = [("accel", 0), ("cruise", int(rng.integers(150, 600))),
               ("decel", 0), ("idle", int(rng.integers(30, 180)))]
    s, dur = seg.pop(0)
    if s == "idle":
        for _ in range(dur):
            if i >= N: break
            v = max(0.0, v - 4); speed[i] = v; state[i] = "idle"; i += 1
    elif s == "accel":
        target = rng.uniform(60, 100)
        while v < target and i < N:
            v = min(target, v + rng.uniform(1.0, 2.5)); speed[i] = v; state[i] = "accel"; i += 1
    elif s == "cruise":
        target = v
        for _ in range(dur):
            if i >= N: break
            target = np.clip(target + rng.normal(0, 1.2), 60, 100)
            v = target; speed[i] = v; state[i] = "cruise"; i += 1
    elif s == "decel":
        while v > 5 and i < N:
            v = max(0.0, v - rng.uniform(1.5, 3.5)); speed[i] = v; state[i] = "decel"; i += 1

# ---------- 2. Signals ----------
rpm = np.where(speed < 1, rng.normal(800, 35, N), 1100 + speed * 20 + rng.normal(0, 90, N))
rpm = np.clip(rpm, 650, 3600)

vib = np.where(speed < 1, rng.normal(0.10, 0.02, N),
               0.12 + speed * 0.0030 + rng.normal(0, 0.035, N))
vib = np.clip(vib, 0.03, None)

# coolant-style temperature: cold start warm-up + first-order lag towards load target
temp = np.empty(N); t = 38.0
for k in range(N):
    target = 86 if state[k] == "idle" else 90 + (speed[k] - 60) * 0.06 if speed[k] > 0 else 88
    t += (target - t) * (0.010 if t < 80 else 0.020) + rng.normal(0, 0.25)
    temp[k] = t

# node placement offsets (applied before labelling so labels match the thresholds)
node_ids = np.array(["0x101", "0x102", "0x103"])    # engine / transmission / chassis TX nodes
nid = rng.integers(0, 3, N)
temp = temp + np.array([0.0, -2.0, -3.5])[nid]

# ---------- 3. Fault episodes (~3% of rows, contiguous like real faults) ----------
fault = np.zeros(N, dtype=int)
target_rows = int(0.032 * N)   # ~3% remain after threshold filtering
kinds = [101, 102, 103]             # 101 overheating, 102 abnormal vibration, 103 both
used, placed = np.zeros(N, bool), 0
while placed < target_rows:
    L = int(rng.integers(20, 60)); L = min(L, target_rows - placed) if target_rows - placed < 20 else L
    a = int(rng.integers(700, N - L - 5))          # skip the cold-start warm-up
    if used[max(0, a - 120):a + L + 120].any(): continue
    k = rng.choice(kinds, p=[0.45, 0.40, 0.15])
    ramp = np.linspace(0, 1, L) ** 0.7
    if k in (101, 103):
        temp[a:a + L] = np.maximum(temp[a:a + L], 98 + ramp * rng.uniform(12, 28) + rng.normal(0, 0.6, L))
    if k in (102, 103):
        vib[a:a + L] = np.maximum(vib[a:a + L], 0.9 + ramp * rng.uniform(0.3, 1.4) + rng.normal(0, 0.12, L))
    fault[a:a + L] = k; used[a:a + L] = True; placed += L

# round to logged precision BEFORE labelling so labels match the thresholds exactly
temp, vib = temp.round(1), vib.round(3)
# temperature must cross 105 C to be labelled overheating; vibration must cross 0.8 g
fault = np.where((fault == 101) & (temp < 105), 0, fault)
fault = np.where((fault == 102) & (vib < 0.8), 0, fault)
fault = np.where((fault == 103) & (temp < 105) & (vib < 0.8), 0, fault)
fault = np.where((fault == 103) & (temp < 105), 102, fault)
fault = np.where((fault == 103) & (vib < 0.8), 101, fault)

# ---------- 4. Nodes, timestamps, labels ----------
ts = pd.date_range("2024-01-01 00:00:00", periods=N, freq="1s").strftime("%Y-%m-%d %H:%M:%S")

df = pd.DataFrame({
    "timestamp": ts, "node_id": node_ids[nid],
    "temp_C": temp.round(1), "vibration_g": vib.round(3), "rpm": rpm.round().astype(int),
    "fault_code": fault, "alarm_flag": (fault != 0).astype(int)})
df.to_csv("dataset.csv", index=False)
print(df.shape, "| fault rows: %d (%.2f%%)" % (df.alarm_flag.sum(), 100 * df.alarm_flag.mean()))
