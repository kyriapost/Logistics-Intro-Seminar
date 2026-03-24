from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import DataConfig

EXPECTED_COLUMNS = {
    "Start": "start",
    "End": "end",
    "Volume (kWh)": "net_demand_kwh",
    "Price (EUR/kWh)": "price_eur_per_kwh",
}


def load_timeseries(data_config: DataConfig) -> tuple[pd.DataFrame, float]:
    path = Path(data_config.csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Could not find data file: {path}")

    df = pd.read_csv(path).rename(columns=EXPECTED_COLUMNS)
    missing = [original for original, renamed in EXPECTED_COLUMNS.items() if renamed not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])
    df = df[["start", "end", "net_demand_kwh", "price_eur_per_kwh"]].copy()
    df["net_demand_kwh"] = df["net_demand_kwh"].astype(float)
    df["price_eur_per_kwh"] = df["price_eur_per_kwh"].astype(float)

    if data_config.start_index:
        df = df.iloc[data_config.start_index :].copy()
    if data_config.periods is not None:
        df = df.iloc[: data_config.periods].copy()
    if df.empty:
        raise ValueError("No data left after applying start_index and periods.")

    df.reset_index(drop=True, inplace=True)
    time_step_hours = infer_time_step_hours(df)
    return df, time_step_hours


def infer_time_step_hours(df: pd.DataFrame) -> float:
    delta = df.loc[0, "end"] - df.loc[0, "start"]
    return delta.total_seconds() / 3600.0


def apply_timeseries_modifiers(
    df: pd.DataFrame,
    *,
    price_scale: float = 1.0,
    price_shift: float = 0.0,
    flatten_prices: bool = False,
    demand_scale: float = 1.0,
    demand_shift: float = 0.0,
) -> pd.DataFrame:
    modified = df.copy()
    if flatten_prices:
        modified["price_eur_per_kwh"] = modified["price_eur_per_kwh"].mean()
    modified["price_eur_per_kwh"] = modified["price_eur_per_kwh"] * price_scale + price_shift
    modified["net_demand_kwh"] = modified["net_demand_kwh"] * demand_scale + demand_shift
    return modified
