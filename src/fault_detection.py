"""Fault detection: (1) rule engine used on the receiver node, (2) ML models for early warning."""
import pandas as pd

TEMP_WARN_C = 105.0     # overheating threshold
VIB_WARN_G = 0.80       # abnormal vibration threshold
FAULT_NAMES = {0: "OK", 101: "OVERHEAT", 102: "VIBRATION", 103: "OVERHEAT+VIB"}


def rule_fault_code(temp_c: float, vib_g: float) -> int:
    hot, shaky = temp_c >= TEMP_WARN_C, vib_g >= VIB_WARN_G
    return 103 if hot and shaky else 101 if hot else 102 if shaky else 0


FEATURES = ["temp_C", "vibration_g", "rpm", "temp_mean5", "temp_slope5", "vib_mean5", "vib_std5", "rpm_std5"]


def add_window_features(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Causal rolling features (only past samples) so they can run on the live receiver."""
    out = df.copy()
    out["temp_mean5"] = out.temp_C.rolling(window, min_periods=1).mean()
    out["temp_slope5"] = out.temp_C.diff(window - 1).fillna(0) / (window - 1)
    out["vib_mean5"] = out.vibration_g.rolling(window, min_periods=1).mean()
    out["vib_std5"] = out.vibration_g.rolling(window, min_periods=2).std().fillna(0)
    out["rpm_std5"] = out.rpm.rolling(window, min_periods=2).std().fillna(0)
    return out


def split_time(df, frac=0.7):
    """Chronological split (no shuffling) so fault episodes never leak between train and test."""
    k = int(len(df) * frac)
    return df.iloc[:k], df.iloc[k:]
