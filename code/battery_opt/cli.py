from __future__ import annotations

import argparse
from pathlib import Path

from .analysis.assignment4 import run_assignment4_suite, run_formulation_benchmark
from .analysis.assignment5 import run_assignment5_suite
from .analysis.assignment6 import run_assignment6_suite
from .analysis.assignment7 import run_assignment7_skeleton
from .config import (
    Formulation,
    load_assignment4_config,
    load_assignment5_config,
    load_assignment6_config,
    load_assignment7_config,
    load_case_config,
)
from .solve import solve_case


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Battery optimization project scaffold.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    solve_parser = subparsers.add_parser("solve", help="Solve one formulation for the configured case.")
    solve_parser.add_argument("--config", required=True, help="Path to case config JSON.")
    solve_parser.add_argument("--formulation", choices=[item.value for item in Formulation], required=True)
    solve_parser.add_argument("--relax-binaries", action="store_true")
    solve_parser.add_argument("--output", help="Optional CSV path for the resulting schedule.")

    benchmark_parser = subparsers.add_parser("benchmark", help="Compare both formulations on the base case.")
    benchmark_parser.add_argument("--config", required=True, help="Path to case config JSON.")
    benchmark_parser.add_argument("--output", help="Optional CSV path for the benchmark table.")

    assignment4_parser = subparsers.add_parser(
        "assignment4",
        help="Run the assignment 4 analysis suite.",
    )
    assignment4_parser.add_argument("--config", required=True, help="Path to case config JSON.")
    assignment4_parser.add_argument(
        "--analysis-config",
        required=True,
        help="Path to assignment 4 analysis config JSON.",
    )
    assignment4_parser.add_argument("--output-dir", required=True, help="Directory for CSVs and plots.")

    assignment5_parser = subparsers.add_parser("assignment5", help="Run the assignment 5 grid-fee study.")
    assignment5_parser.add_argument("--config", required=True, help="Path to case config JSON.")
    assignment5_parser.add_argument("--analysis-config", required=True, help="Path to assignment 5 config JSON.")
    assignment5_parser.add_argument("--output-dir", required=True, help="Directory for CSVs and plots.")

    assignment6_parser = subparsers.add_parser("assignment6", help="Run the assignment 6 degradation study.")
    assignment6_parser.add_argument("--config", required=True, help="Path to case config JSON.")
    assignment6_parser.add_argument("--analysis-config", required=True, help="Path to assignment 6 config JSON.")
    assignment6_parser.add_argument("--output-dir", required=True, help="Directory for CSVs and plots.")

    assignment7_parser = subparsers.add_parser("assignment7", help="Run the assignment 7 extension skeleton.")
    assignment7_parser.add_argument("--config", required=True, help="Path to case config JSON.")
    assignment7_parser.add_argument("--analysis-config", required=True, help="Path to assignment 7 config JSON.")
    assignment7_parser.add_argument("--output-dir", required=True, help="Directory for CSV outputs.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "solve":
        case_config = load_case_config(args.config)
        result = solve_case(case_config, args.formulation, relax_binaries=args.relax_binaries)
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            result.schedule.to_csv(args.output, index=False)
        print(
            f"formulation={result.formulation} "
            f"relaxed={result.relaxed} "
            f"status={result.status_name} "
            f"objective_eur={result.objective_value_eur} "
            f"runtime_seconds={result.runtime_seconds:.4f}"
        )
        return

    if args.command == "benchmark":
        case_config = load_case_config(args.config)
        benchmark = run_formulation_benchmark(case_config)
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            benchmark.to_csv(args.output, index=False)
        print(benchmark.to_string(index=False))
        return

    if args.command == "assignment4":
        case_config = load_case_config(args.config)
        analysis_config = load_assignment4_config(args.analysis_config)
        outputs = run_assignment4_suite(case_config, analysis_config, args.output_dir)
        for name, table in outputs.items():
            print(f"\n{name}")
            print(table.to_string(index=False))
        return

    if args.command == "assignment5":
        case_config = load_case_config(args.config)
        analysis_config = load_assignment5_config(args.analysis_config)
        outputs = run_assignment5_suite(case_config, analysis_config, args.output_dir)
        for name, table in outputs.items():
            print(f"\n{name}")
            print(table.to_string(index=False))
        return

    if args.command == "assignment6":
        case_config = load_case_config(args.config)
        analysis_config = load_assignment6_config(args.analysis_config)
        outputs = run_assignment6_suite(case_config, analysis_config, args.output_dir)
        for name, table in outputs.items():
            print(f"\n{name}")
            print(table.to_string(index=False))
        return

    if args.command == "assignment7":
        case_config = load_case_config(args.config)
        analysis_config = load_assignment7_config(args.analysis_config)
        outputs = run_assignment7_skeleton(case_config, analysis_config, args.output_dir)
        for name, table in outputs.items():
            print(f"\n{name}")
            print(table.to_string(index=False))
        return


if __name__ == "__main__":
    main()
