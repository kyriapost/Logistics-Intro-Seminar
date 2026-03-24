from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class OptimizationResult:
    formulation: str
    relaxed: bool
    status_code: int
    status_name: str
    objective_value_eur: float | None
    runtime_seconds: float
    mip_gap: float | None
    best_bound: float | None
    node_count: float | None
    schedule: pd.DataFrame
    summary: dict[str, Any]
