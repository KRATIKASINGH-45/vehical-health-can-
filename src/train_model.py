"""Train and evaluate detectors on data/dataset.csv (chronological 70/30 split).

 A. Rule baseline            : temp >= 105 C or vibration >= 0.8 g  (what the receiver firmware runs)
 B. RandomForest classifier  : supervised, causal window features -> alarm_flag
 C. IsolationForest          : unsupervised (no labels used for fitting) -> alarm_flag
 D. Early-warning RandomForest: will an alarm start within the next 10 s? (only on not-yet-alarmed rows)

Outputs: outputs/model_rf.pkl, outputs/metrics.json, outputs/figures/fig_*.png
"""
import json, pickle, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import (precision_score, recall_score, f1_score, accuracy_score,
                             confusion_matrix, roc_auc_score, roc_curve)
from .fault_detection import add_window_features, split_time, FEATURES, rule_fault_code

HORIZON = 10


def prf(y, p):
    return dict(accuracy=round(accuracy_score(y, p), 4), precision=round(precision_score(y, p, zero_division=0), 4),
                recall=round(recall_score(y, p, zero_division=0), 4), f1=round(f1_score(y, p, zero_division=0), 4),
                confusion_matrix=confusion_matrix(y, p, labels=[0, 1]).tolist())


def load(path="data/dataset.csv"):
    df = pd.read_csv(path, dtype={"node_id": str})
    return add_window_features(df)


def future_alarm(alarm, horizon=HORIZON):
    a = np.asarray(alarm)
    out = np.zeros(len(a), dtype=int)
    for k in range(len(a)):
        out[k] = int(a[k + 1:k + 1 + horizon].any())
    return out


def main(path="data/dataset.csv", out="outputs"):
    os.makedirs(f"{out}/figures", exist_ok=True)
    df = load(path)
    train, test = split_time(df, 0.7)
    m = dict(train_rows=len(train), test_rows=len(test), test_fault_rows=int(test.alarm_flag.sum()),
             train_fault_rows=int(train.alarm_flag.sum()))

    # A. rule baseline
    rule_pred = np.array([int(rule_fault_code(t, v) != 0) for t, v in zip(test.temp_C, test.vibration_g)])
    m["rule_baseline"] = prf(test.alarm_flag, rule_pred)

    # B. supervised RF
    rf = RandomForestClassifier(n_estimators=150, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1)
    rf.fit(train[FEATURES], train.alarm_flag)
    proba = rf.predict_proba(test[FEATURES])[:, 1]
    m["random_forest"] = prf(test.alarm_flag, (proba >= 0.5).astype(int))
    m["random_forest"]["roc_auc"] = round(roc_auc_score(test.alarm_flag, proba), 4)
    m["rf_feature_importance"] = {f: round(float(i), 4) for f, i in sorted(zip(FEATURES, rf.feature_importances_), key=lambda x: -x[1])}
    with open(f"{out}/model_rf.pkl", "wb") as fh:
        pickle.dump(rf, fh)

    # C. unsupervised IsolationForest (fit WITHOUT labels, on the training window)
    raw = ["temp_C", "vibration_g", "rpm"]
    iso = IsolationForest(n_estimators=200, contamination=0.03, random_state=42).fit(train[raw])
    iso_pred = (iso.predict(test[raw]) == -1).astype(int)
    iso_score = -iso.score_samples(test[raw])
    m["isolation_forest"] = prf(test.alarm_flag, iso_pred)
    m["isolation_forest"]["roc_auc"] = round(roc_auc_score(test.alarm_flag, iso_score), 4)

    # D. early warning: alarm starting within the next HORIZON seconds, among rows not yet alarmed
    df["future_alarm"] = future_alarm(df.alarm_flag)
    tr, te = split_time(df, 0.7)
    tr, te = tr[tr.alarm_flag == 0], te[te.alarm_flag == 0]
    ew = RandomForestClassifier(n_estimators=150, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1)
    ew.fit(tr[FEATURES], tr.future_alarm)
    ew_p = ew.predict_proba(te[FEATURES])[:, 1]
    m["early_warning"] = prf(te.future_alarm, (ew_p >= 0.5).astype(int))
    m["early_warning"].update(horizon_s=HORIZON, test_positive_rows=int(te.future_alarm.sum()),
                              roc_auc=round(roc_auc_score(te.future_alarm, ew_p), 4) if te.future_alarm.nunique() > 1 else None)

    # ---- figures ----
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
    for a, (name, key) in zip(ax, [("Rule baseline", "rule_baseline"), ("Random Forest", "random_forest")]):
        cm = np.array(m[key]["confusion_matrix"]); a.imshow(cm, cmap="Blues")
        for (i, j), v in np.ndenumerate(cm): a.text(j, i, str(v), ha="center", va="center", color="white" if v > cm.max() / 2 else "black", fontsize=12)
        a.set_xticks([0, 1], ["Normal", "Fault"]); a.set_yticks([0, 1], ["Normal", "Fault"])
        a.set_xlabel("Predicted"); a.set_ylabel("Actual"); a.set_title(name)
    plt.tight_layout(); plt.savefig(f"{out}/figures/fig_confusion.png", dpi=130); plt.close()

    plt.figure(figsize=(5.2, 4))
    for name, y, s in [("Random Forest", test.alarm_flag, proba), ("Isolation Forest (unsupervised)", test.alarm_flag, iso_score)]:
        fpr, tpr, _ = roc_curve(y, s); plt.plot(fpr, tpr, label=name)
    plt.plot([0, 1], [0, 1], "k--", lw=0.8); plt.xlabel("False positive rate"); plt.ylabel("True positive rate")
    plt.title("ROC on held-out test window"); plt.legend(loc="lower right"); plt.tight_layout()
    plt.savefig(f"{out}/figures/fig_roc.png", dpi=130); plt.close()

    imp = m["rf_feature_importance"]
    plt.figure(figsize=(5.5, 3.4)); plt.barh(list(imp)[::-1], list(imp.values())[::-1], color="#2a6f97")
    plt.xlabel("Importance"); plt.title("Random Forest feature importance"); plt.tight_layout()
    plt.savefig(f"{out}/figures/fig_feature_importance.png", dpi=130); plt.close()

    with open(f"{out}/metrics.json", "w") as fh:
        json.dump(m, fh, indent=2)
    return m


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
