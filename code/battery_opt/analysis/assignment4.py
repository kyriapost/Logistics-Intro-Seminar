from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from ..config import Assignment4Config, CaseConfig, Formulation, LPScenarioConfig
from .common import apply_scenario_overrides, build_fraction_windows, load_analysis_data, safe_solve


def run_formulation_benchmark(case_config: CaseConfig) -> pd.DataFrame:
    base_data = load_analysis_data(case_config, "configured_case")
    records = []
    for formulation in Formulation:
        result, error = safe_solve(case_config, formulation, prepared_data=base_data)
        if error is not None:
            records.append(_error_record(formulation.value, len(base_data), "full_horizon", error))
        else:
            records.append(_result_record(result, len(base_data), "full_horizon"))
    return pd.DataFrame(records)


def run_horizon_study(case_config: CaseConfig, assignment4_config: Assignment4Config) -> pd.DataFrame:
    base_data = load_analysis_data(case_config, assignment4_config.window_dataset_scope)
    windows = build_fraction_windows(base_data, assignment4_config.horizon_windows)
    records = []
    for window in windows:
        for formulation in Formulation:
            result, error = safe_solve(case_config, formulation, prepared_data=window.data)
            if error is not None:
                record = _error_record(formulation.value, len(window.data), "horizon_sweep", error)
            else:
                record = _result_record(result, len(window.data), "horizon_sweep")
            record.update(
                {
                    "window_label": window.label,
                    "window_fraction": window.fraction,
                    "window_position": window.position.value,
                    "window_start_index": window.start_index,
                    "window_end_index": window.end_index - 1,
                    "window_start_timestamp": window.data.loc[0, "start"],
                    "window_end_timestamp": window.data.loc[len(window.data) - 1, "end"],
                }
            )
            records.append(record)
    return pd.DataFrame(records)


def run_lp_relaxation_study(
    case_config: CaseConfig,
    scenarios: list[LPScenarioConfig] | tuple[LPScenarioConfig, ...],
    *,
    objective_tolerance: float = 1e-6,
    schedule_tolerance: float = 1e-6,
) -> pd.DataFrame:
    base_data = load_analysis_data(case_config, "configured_case")
    records = []
    for scenario in scenarios:
        scenario_case, scenario_data = apply_scenario_overrides(case_config, base_data, scenario)
        for formulation in Formulation:
            mip_result, mip_error = safe_solve(
                scenario_case,
                formulation,
                relax_binaries=False,
                prepared_data=scenario_data,
            )
            lp_result, lp_error = safe_solve(
                scenario_case,
                formulation,
                relax_binaries=True,
                prepared_data=scenario_data,
            )
            if mip_error is not None or lp_error is not None:
                records.append(
                    {
                        "scenario": scenario.name,
                        "formulation": formulation.value,
                        "mip_status": mip_error or mip_result.status_name,
                        "lp_status": lp_error or lp_result.status_name,
                        "mip_objective_eur": None if mip_result is None else mip_result.objective_value_eur,
                        "lp_objective_eur": None if lp_result is None else lp_result.objective_value_eur,
                        "objective_gap_eur": None,
                        "same_objective": False,
                        "same_schedule": False,
                        "schedule_gap": float("inf"),
                        "lp_fractional_mode_count": None if lp_result is None else lp_result.summary["fractional_mode_count"],
                        "lp_max_mode_fractionality": None if lp_result is None else lp_result.summary["max_mode_fractionality"],
                        "mip_runtime_seconds": None if mip_result is None else mip_result.runtime_seconds,
                        "lp_runtime_seconds": None if lp_result is None else lp_result.runtime_seconds,
                        "periods": len(scenario_data),
                    }
                )
                continue
            schedule_distance = _max_schedule_gap(mip_result.schedule, lp_result.schedule)
            objective_gap = None
            if mip_result.objective_value_eur is not None and lp_result.objective_value_eur is not None:
                objective_gap = lp_result.objective_value_eur - mip_result.objective_value_eur
            records.append(
                {
                    "scenario": scenario.name,
                    "formulation": formulation.value,
                    "mip_status": mip_result.status_name,
                    "lp_status": lp_result.status_name,
                    "mip_objective_eur": mip_result.objective_value_eur,
                    "lp_objective_eur": lp_result.objective_value_eur,
                    "objective_gap_eur": objective_gap,
                    "same_objective": (
                        objective_gap is not None and abs(objective_gap) <= objective_tolerance
                    ),
                    "same_schedule": schedule_distance <= schedule_tolerance,
                    "schedule_gap": schedule_distance,
                    "lp_fractional_mode_count": lp_result.summary["fractional_mode_count"],
                    "lp_max_mode_fractionality": lp_result.summary["max_mode_fractionality"],
                    "mip_runtime_seconds": mip_result.runtime_seconds,
                    "lp_runtime_seconds": lp_result.runtime_seconds,
                    "periods": len(scenario_data),
                }
            )
    return pd.DataFrame(records)


def run_assignment4_suite(
    case_config: CaseConfig,
    assignment4_config: Assignment4Config,
    output_dir: str | Path,
) -> dict[str, pd.DataFrame]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results: dict[str, pd.DataFrame] = {}
    if assignment4_config.benchmark_full_horizon:
        benchmark = run_formulation_benchmark(case_config)
        benchmark.to_csv(output_path / "benchmark_full_horizon.csv", index=False)
        results["benchmark_full_horizon"] = benchmark

    if assignment4_config.horizon_windows:
        horizons = run_horizon_study(case_config, assignment4_config)
        horizons.to_csv(output_path / "assignment4_horizon_study.csv", index=False)
        _plot_horizon_runtime(horizons, output_path / "assignment4_runtime_by_horizon.png")
        results["assignment4_horizon_study"] = horizons

    if assignment4_config.lp_scenarios:
        lp_results = run_lp_relaxation_study(
            case_config,
            assignment4_config.lp_scenarios,
            objective_tolerance=assignment4_config.objective_tolerance,
            schedule_tolerance=assignment4_config.schedule_tolerance,
        )
        lp_summary = summarize_lp_relaxation_study(lp_results)
        lp_results.to_csv(output_path / "assignment4_lp_relaxation.csv", index=False)
        lp_summary.to_csv(output_path / "assignment4_lp_relaxation_summary.csv", index=False)
        _plot_lp_gaps(lp_results, output_path / "assignment4_lp_gap_by_scenario.png")
        results["assignment4_lp_relaxation"] = lp_results
        results["assignment4_lp_relaxation_summary"] = lp_summary

    return results


def summarize_lp_relaxation_study(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame()
    summary = (
        results.groupby("formulation", as_index=False)
        .agg(
            scenario_count=("scenario", "count"),
            same_objective_count=("same_objective", "sum"),
            same_schedule_count=("same_schedule", "sum"),
            avg_lp_fractional_mode_count=("lp_fractional_mode_count", "mean"),
            max_objective_gap_eur=("objective_gap_eur", "max"),
            avg_mip_runtime_seconds=("mip_runtime_seconds", "mean"),
            avg_lp_runtime_seconds=("lp_runtime_seconds", "mean"),
        )
        .sort_values("formulation")
    )
    return summary


def _max_schedule_gap(mip_schedule: pd.DataFrame, lp_schedule: pd.DataFrame) -> float:
    if mip_schedule.empty or lp_schedule.empty:
        return float("inf")
    columns = ["charge_kw", "discharge_kw", "soc_kwh", "net_grid_kwh"]
    max_gap = 0.0
    for column in columns:
        gap = (mip_schedule[column] - lp_schedule[column]).abs().max()
        max_gap = max(max_gap, float(gap))
    return max_gap


def _result_record(result, periods: int, analysis_name: str) -> dict[str, float | str | int | None]:
    return {
        "analysis": analysis_name,
        "formulation": result.formulation,
        "relaxed": result.relaxed,
        "status": result.status_name,
        "periods": periods,
        "objective_eur": result.objective_value_eur,
        "runtime_seconds": result.runtime_seconds,
        "mip_gap": result.mip_gap,
        "node_count": result.node_count,
        "fractional_mode_count": result.summary["fractional_mode_count"],
    }


def _error_record(formulation: str, periods: int, analysis_name: str, error: str) -> dict[str, float | str | int | None]:
    return {
        "analysis": analysis_name,
        "formulation": formulation,
        "relaxed": False,
        "status": error,
        "periods": periods,
        "objective_eur": None,
        "runtime_seconds": None,
        "mip_gap": None,
        "node_count": None,
        "fractional_mode_count": None,
    }


def _plot_horizon_runtime(results: pd.DataFrame, output_path: Path) -> None:
    if results.empty:
        return
    plot_data = results.dropna(subset=["runtime_seconds"]).copy()
    if plot_data.empty:
        return
    pivot = plot_data.pivot(index="window_label", columns="formulation", values="runtime_seconds")
    ax = pivot.plot(kind="bar", figsize=(10, 4))
    ax.set_title("Runtime by Fractional Window")
    ax.set_xlabel("Window")
    ax.set_ylabel("Runtime (s)")
    ax.grid(True, alpha=0.3)
    ax.figure.tight_layout()
    ax.figure.savefig(output_path, dpi=150)
    plt.close(ax.figure)


def _plot_lp_gaps(results: pd.DataFrame, output_path: Path) -> None:
    if results.empty:
        return
    plot_data = results.copy()
    plot_data["label"] = plot_data["scenario"] + " | " + plot_data["formulation"]
    ax = plot_data.plot.bar(x="label", y="objective_gap_eur", figsize=(10, 4), legend=False)
    ax.set_title("LP Relaxation Objective Gap by Scenario")
    ax.set_xlabel("Scenario")
    ax.set_ylabel("LP objective - MIP objective (EUR)")
    ax.grid(True, axis="y", alpha=0.3)
    ax.figure.tight_layout()
    ax.figure.savefig(output_path, dpi=150)
    plt.close(ax.figure)
