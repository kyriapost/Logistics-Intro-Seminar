from __future__ import annotations

from typing import Callable

import gurobipy as gp
import pandas as pd
from gurobipy import GRB

from .config import CaseConfig, Formulation
from .data import load_timeseries
from .formulations import build_basic_model, build_tighter_model
from .formulations.common import ModelArtifacts
from .metrics import summarize_schedule
from .results import OptimizationResult

BUILDERS: dict[Formulation, Callable[..., ModelArtifacts]] = {
    Formulation.BASIC: build_basic_model,
    Formulation.TIGHTER: build_tighter_model,
}

STATUS_NAMES = {
    GRB.OPTIMAL: "OPTIMAL",
    GRB.INFEASIBLE: "INFEASIBLE",
    GRB.TIME_LIMIT: "TIME_LIMIT",
    GRB.SUBOPTIMAL: "SUBOPTIMAL",
    GRB.INF_OR_UNBD: "INF_OR_UNBD",
    GRB.UNBOUNDED: "UNBOUNDED",
}


def solve_case(
    case_config: CaseConfig,
    formulation: Formulation | str,
    *,
    relax_binaries: bool = False,
    prepared_data: pd.DataFrame | None = None,
) -> OptimizationResult:
    formulation = Formulation(formulation)
    if prepared_data is None:
        data, inferred_dt = load_timeseries(case_config.data)
    else:
        data = prepared_data.copy().reset_index(drop=True)
        inferred_dt = case_config.time_step_hours
        if inferred_dt is None:
            delta = data.loc[0, "end"] - data.loc[0, "start"]
            inferred_dt = delta.total_seconds() / 3600.0

    effective_config = case_config if case_config.time_step_hours else _with_time_step(case_config, inferred_dt)
    artifacts = BUILDERS[formulation](effective_config, data, relax_binaries=relax_binaries)
    artifacts.model.optimize()
    schedule = _extract_schedule(artifacts)

    summary = summarize_schedule(schedule, effective_config.battery)
    summary["time_step_hours"] = artifacts.time_step_hours

    return OptimizationResult(
        formulation=formulation.value,
        relaxed=relax_binaries,
        status_code=artifacts.model.Status,
        status_name=STATUS_NAMES.get(artifacts.model.Status, str(artifacts.model.Status)),
        objective_value_eur=_safe_model_attr(artifacts.model, "ObjVal"),
        runtime_seconds=float(artifacts.model.Runtime),
        mip_gap=_safe_model_attr(artifacts.model, "MIPGap"),
        best_bound=_safe_model_attr(artifacts.model, "ObjBound"),
        node_count=_safe_model_attr(artifacts.model, "NodeCount"),
        schedule=schedule,
        summary=summary,
    )


def _extract_schedule(artifacts: ModelArtifacts) -> pd.DataFrame:
    if artifacts.model.SolCount == 0:
        return pd.DataFrame()

    df = artifacts.data.copy()
    dt = artifacts.time_step_hours
    df["charge_kw"] = [artifacts.charge_kw[t].X for t in range(len(df))]
    df["discharge_kw"] = [artifacts.discharge_kw[t].X for t in range(len(df))]
    df["soc_kwh"] = [artifacts.soc[t].X for t in range(len(df))]
    df["mode"] = [artifacts.mode[t].X for t in range(len(df))]
    df["net_grid_kwh"] = [artifacts.net_grid_kwh[t].X for t in range(len(df))]
    df["charge_kwh"] = df["charge_kw"] * dt
    df["discharge_kwh"] = df["discharge_kw"] * dt
    df["grid_import_kwh"] = df["net_grid_kwh"].clip(lower=0.0)
    df["grid_export_kwh"] = (-df["net_grid_kwh"]).clip(lower=0.0)
    return df


def _safe_model_attr(model: gp.Model, attribute: str) -> float | None:
    try:
        return float(getattr(model, attribute))
    except (gp.GurobiError, AttributeError):
        return None


def _with_time_step(case_config: CaseConfig, time_step_hours: float) -> CaseConfig:
    return CaseConfig(
        name=case_config.name,
        data=case_config.data,
        battery=case_config.battery,
        solver=case_config.solver,
        time_step_hours=time_step_hours,
    )
