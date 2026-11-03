"""One command to reproduce everything:  python run_all.py
EDA -> model training -> CAN simulation -> dashboard -> unit tests."""
import subprocess, sys, json
from src import eda, train_model, simulate, dashboard, robustness

print("[1/6] EDA ..."); e = eda.main(); print(f"      rows={e['rows']} faults={e['fault_pct']}%")
print("[2/6] Training detectors ..."); m = train_model.main()
print(f"      RF F1={m['random_forest']['f1']}  IsolationForest F1={m['isolation_forest']['f1']}")
print("[3/6] CAN simulation ..."); s, _ = simulate.run()
print(f"      decoded {s['frames_decoded']}/{s['frames_sent']} frames, episodes detected {s['episodes_detected']}/{s['fault_episodes']}")
print("[4/6] Dashboard ..."); print("     ", dashboard.main())
print("[5/6] Robustness sweep ..."); print(robustness.main().to_string(index=False))
print("[6/6] Unit tests ...")
sys.exit(subprocess.call([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]))
