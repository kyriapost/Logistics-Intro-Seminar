from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import gurobipy as gp
import pandas as pd
from gurobipy import GRB

from ..config import CaseConfig, Formulation


@dataclass
class ModelArtifacts:
    model: gp.Model
    formulation: Formulation
    data: pd.DataFrame
    time_step_hours: float
    soc: gp.tupledict
    charge_kw: gp.tupledict
    discharge_kw: gp.tupledict
    mode: gp.tupledict
    net_grid_kwh: gp.tupledict


def build_common_model(
    case_config: CaseConfig,
    data: pd.DataFrame,
    formulation: Formulation,
    *,
    relax_binaries: bool,
) -> ModelArtifacts:
    battery = case_config.battery
    dt = case_config.time_step_hours or _infer_dt(data)
    periods = range(len(data))

    model = gp.Model(f"{case_config.name}_{formulation.value}")
    _apply_solver_config(model, case_config)

    soc = model.addVars(periods, lb=0.0, name="soc_kwh")
    charge_kw = model.addVars(periods, lb=0.0, name="charge_kw")
    discharge_kw = model.addVars(periods, lb=0.0, name="discharge_kw")
    net_grid_kwh = model.addVars(periods, lb=-GRB.INFINITY, name="net_grid_kwh")
    mode = model.addVars(
        periods,
        lb=0.0,
        ub=1.0,
        vtype=GRB.CONTINUOUS if relax_binaries else GRB.BINARY,
        name="mode",
    )

    fee_penalty = gp.LinExpr()
    if battery.grid_fee_eur_per_kwh > 0.0:
        grid_import_kwh = model.addVars(periods, lb=0.0, name="grid_import_kwh")
        grid_export_kwh = model.addVars(periods, lb=0.0, name="grid_export_kwh")
        for t in periods:
            model.addConstr(
                net_grid_kwh[t] == grid_import_kwh[t] - grid_export_kwh[t],
                name=f"net_grid_split[{t}]",
            )
        fee_penalty = gp.quicksum(
            battery.grid_fee_eur_per_kwh * (grid_import_kwh[t] + grid_export_kwh[t])
            for t in periods
        )

    for t in periods:
        previous_soc = battery.initial_soc_kwh if t == 0 else soc[t - 1]
        model.addConstr(
            soc[t]
            == previous_soc
            + battery.charge_efficiency * charge_kw[t] * dt
            - discharge_kw[t] * dt / battery.discharge_efficiency,
            name=f"soc_balance[{t}]",
        )
        model.addConstr(soc[t] >= battery.soc_min_kwh, name=f"soc_min[{t}]")
        model.addConstr(soc[t] <= battery.soc_max_kwh, name=f"soc_max[{t}]")
        model.addConstr(
            charge_kw[t] <= battery.charge_power_limit_kw * mode[t],
            name=f"charge_limit[{t}]",
        )
        model.addConstr(
            discharge_kw[t] <= battery.discharge_power_limit_kw * (1.0 - mode[t]),
            name=f"discharge_limit[{t}]",
        )
        model.addConstr(
            net_grid_kwh[t]
            == float(data.loc[t, "net_demand_kwh"]) + charge_kw[t] * dt - discharge_kw[t] * dt,
            name=f"grid_balance[{t}]",
        )

    degradation_penalty = gp.quicksum(
        battery.degradation_cost_eur_per_kwh_throughput * (charge_kw[t] + discharge_kw[t]) * dt
        for t in periods
    )
    energy_profit = gp.quicksum(
        -float(data.loc[t, "price_eur_per_kwh"]) * net_grid_kwh[t]
        for t in periods
    )
    model.setObjective(energy_profit - fee_penalty - degradation_penalty, GRB.MAXIMIZE)

    return ModelArtifacts(
        model=model,
        formulation=formulation,
        data=data.copy(),
        time_step_hours=dt,
        soc=soc,
        charge_kw=charge_kw,
        discharge_kw=discharge_kw,
        mode=mode,
        net_grid_kwh=net_grid_kwh,
    )


def previous_soc_value(artifacts: ModelArtifacts, t: int, initial_soc_kwh: float) -> Any:
    return initial_soc_kwh if t == 0 else artifacts.soc[t - 1]


def _apply_solver_config(model: gp.Model, case_config: CaseConfig) -> None:
    model.Params.OutputFlag = case_config.solver.output_flag
    if case_config.solver.time_limit_seconds is not None:
        model.Params.TimeLimit = case_config.solver.time_limit_seconds
    if case_config.solver.mip_gap is not None:
        model.Params.MIPGap = case_config.solver.mip_gap
    if case_config.solver.threads is not None:
        model.Params.Threads = case_config.solver.threads


def _infer_dt(data: pd.DataFrame) -> float:
    delta = data.loc[0, "end"] - data.loc[0, "start"]
    return delta.total_seconds() / 3600.0
