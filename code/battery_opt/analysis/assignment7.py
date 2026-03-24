from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import Assignment7Config, Assignment7ScenarioConfig, CaseConfig
from .common import apply_scenario_overrides, load_analysis_data, safe_solve, window_for_fraction


def run_assignment7_skeleton(
    case_config: CaseConfig,
    assignment7_config: Assignment7Config,
    output_dir: str | Path,
) -> dict[str, pd.DataFrame]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    base_data = load_analysis_data(case_config, assignment7_config.dataset_scope)
    records = []

    for scenario in assignment7_config.scenarios:
        scenario_data = base_data
        window_label = "full_configured_scope"
        if scenario.window_fraction is not None:
            window = window_for_fraction(base_data, scenario.window_fraction, scenario.window_position)
            scenario_data = window.data
            window_label = window.label

        scenario_case, scenario_data = apply_scenario_overrides(case_config, scenario_data, scenario)
        result, error = safe_solve(scenario_case, scenario.formulation, prepared_data=scenario_data)

        if error is not None:
            records.append(
                {
                    "scenario": scenario.name,
                    "description": scenario.description,
                    "formulation": scenario.formulation.value,
                    "window_label": window_label,
                    "status": error,
                    "periods": len(scenario_data),
                    "custom_parameters": str(scenario.custom_parameters),
                }
            )
            continue

        if scenario.save_schedule:
            schedule_path = output_path / f"assignment7_schedule_{scenario.name}.csv"
            result.schedule.to_csv(schedule_path, index=False)

        record = {
            "scenario": scenario.name,
            "description": scenario.description,
            "formulation": scenario.formulation.value,
            "window_label": window_label,
            "status": result.status_name,
            "periods": len(scenario_data),
            "objective_eur": result.objective_value_eur,
            "runtime_seconds": result.runtime_seconds,
            "total_grid_exchange_kwh": result.summary["total_grid_exchange_kwh"],
            "throughput_kwh": result.summary["throughput_kwh"],
            "self_consumption_rate": result.summary["self_consumption_rate"],
            "custom_parameters": str(scenario.custom_parameters),
        }
        record.update(_collect_assignment7_extension_metrics(result.schedule, scenario))
        records.append(record)

    results = pd.DataFrame(records)
    results.to_csv(output_path / "assignment7_extension_scenarios.csv", index=False)
    return {"assignment7_extension_scenarios": results}


def _collect_assignment7_extension_metrics(
    schedule: pd.DataFrame,
    scenario: Assignment7ScenarioConfig,
) -> dict[str, float | str]:
    if schedule.empty:
        return {"extension_metric_1": "", "extension_metric_2": ""}

    # Extension hook:
    # add scenario-specific metrics here without touching the solver layer.
    peak_import = float(schedule["grid_import_kwh"].max())
    peak_export = float(schedule["grid_export_kwh"].max())
    return {
        "extension_metric_1": peak_import,
        "extension_metric_2": peak_export,
    }
