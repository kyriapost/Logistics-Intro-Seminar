# Battery Optimization Project Structure

This scaffold is set up around the two formulations referenced in the case:

- `basic`: Basic Operation MIP
- `tighter`: Tighter Operation MIP

The point of the structure is to keep the model logic stable while letting you change case parameters, dataset length, solver settings, and analysis scenarios from config files instead of rewriting model code.

## Layout

`battery_opt/config.py`
Defines the shared config objects for the case, solver, and assignment 4 scenarios.

`battery_opt/data.py`
Loads and validates `net_demand_and_price.csv`, infers the time step, and applies scenario changes such as modified price patterns.

`battery_opt/formulations/basic.py`
Implements the Basic Operation MIP.

`battery_opt/formulations/tighter.py`
Implements the Tighter Operation MIP by adding the tighter state-of-charge bounds on top of the shared base model.

`battery_opt/solve.py`
Single entry point for solving either formulation or its LP relaxation.

`battery_opt/analysis/assignment4.py`
Contains the analysis runners for assignment 4:

- full-horizon formulation benchmark
- fraction-based horizon scaling study with start, middle, and end windows
- LP-relaxation vs MIP comparisons
- parameter sweeps for price patterns, efficiencies, power limits, and capacity

`battery_opt/analysis/assignment5.py`
Runs the assignment 5 grid-fee study with fee sweeps and battery/grid utilization metrics.

`battery_opt/analysis/assignment6.py`
Runs the assignment 6 degradation study using a linear throughput degradation cost.

`battery_opt/analysis/assignment7.py`
Provides an assignment 7 skeleton with reusable scenario overrides, optional dataset windows, and per-scenario schedule export.

`configs/base_case.json`
Main case parameters. This is the file to edit first when your group confirms the reference battery values.

`configs/assignment4.json`
Defines the assignment 4 fraction windows and LP-relaxation scenarios.

`configs/assignment5.json`
Defines the grid-fee sweep for assignment 5.

`configs/assignment6.json`
Defines the degradation-cost sweep for assignment 6.

`configs/assignment7.json`
Contains extension-template scenarios for assignment 7.

`scripts/run_base_case.py`
Quick script to solve both formulations.

`scripts/run_assignment4.py`
Quick script to run the assignment 4 study and write outputs to `outputs/assignment4`.

`scripts/run_assignment5.py`
Quick script to run the assignment 5 study.

`scripts/run_assignment6.py`
Quick script to run the assignment 6 study.

`scripts/run_assignment7.py`
Quick script to run the assignment 7 skeleton.

## What To Change

Change `configs/base_case.json` for:

- battery capacity limits
- initial state of charge
- charge/discharge limits
- efficiencies
- grid fee and degradation-cost hooks for later assignments
- default dataset horizon

Change `configs/assignment4.json` for:

- fractional window sizes to benchmark
- which part of the dataset to use for each window: `start`, `middle`, `end`
- whether windows are drawn from the configured case subset or the full CSV
- LP-relaxation experiment scenarios
- price-pattern modifications
- efficiency, power-limit, and capacity sweeps

Change `configs/assignment5.json` for:

- formulations to compare
- grid-fee levels between `0` and `0.05` EUR/kWh

Change `configs/assignment6.json` for:

- formulations to compare
- degradation cost values for the linear throughput model

Change `configs/assignment7.json` for:

- custom extension scenarios
- optional window fractions and window positions
- combined policy, technical, or market experiments
- optional schedule export per scenario

## Assignment 4 Coverage

The code includes the analysis paths explicitly mentioned in assignment 4:

- modify data and parameters and rerun the models
- trim the dataset by fraction and sample windows from different parts of it
- compare formulation behavior as the problem size grows
- compare LP relaxations against the integer models
- test when LP and MIP coincide and when they differ
- detect fractional values in the relaxed charging-mode variable
- vary price patterns, efficiencies, charge/discharge limits, and capacity

## Assignment 5 Coverage

The assignment 5 scaffold includes:

- a grid-fee sweep from `0` to `0.05` EUR/kWh
- objective, import/export, and grid-exchange tracking
- battery utilization metrics such as throughput and equivalent cycles
- a self-consumption proxy based on the available net-demand data

## Assignment 6 Coverage

The assignment 6 scaffold includes:

- a linear degradation-cost model based on battery throughput
- degradation sweeps through config
- comparison against the no-degradation baseline
- objective and utilization plots

## Assignment 7 Skeleton

The assignment 7 scaffold is intentionally generic:

- each scenario can override prices, demand, battery parameters, grid fees, and degradation costs
- each scenario can optionally target a start/middle/end fraction window
- each scenario can optionally export its schedule
- the metric collection hook is isolated in `battery_opt/analysis/assignment7.py` so new ideas can be added without rewriting the solver core

## Commands

Solve one formulation:

```powershell
python -m battery_opt.cli solve --config configs/base_case.json --formulation basic --output outputs/basic_schedule.csv
```

Benchmark both formulations on the base horizon:

```powershell
python -m battery_opt.cli benchmark --config configs/base_case.json --output outputs/benchmark.csv
```

Run the assignment 4 suite:

```powershell
python -m battery_opt.cli assignment4 --config configs/base_case.json --analysis-config configs/assignment4.json --output-dir outputs/assignment4
```

Run the assignment 5 suite:

```powershell
python -m battery_opt.cli assignment5 --config configs/base_case.json --analysis-config configs/assignment5.json --output-dir outputs/assignment5
```

Run the assignment 6 suite:

```powershell
python -m battery_opt.cli assignment6 --config configs/base_case.json --analysis-config configs/assignment6.json --output-dir outputs/assignment6
```

Run the assignment 7 skeleton:

```powershell
python -m battery_opt.cli assignment7 --config configs/base_case.json --analysis-config configs/assignment7.json --output-dir outputs/assignment7
```

## Notes

- The formulas follow the paper structure with `soc_kwh`, `charge_kw`, `discharge_kw`, and the binary `mode` variable.
- The default `configs/base_case.json` values are example values. Replace them with the exact case reference values before your final runs.
- Assignment 5 uses a self-consumption proxy because the dataset provides net demand rather than separate consumption and PV series.
- Assignment 6 currently uses a linear throughput degradation model because it stays compatible with the MIP framework and is easy to extend later.
- If you switch assignment 4 windows to `full_dataset`, larger fractions may exceed the local size-limited Gurobi license. The code records those runs as errors instead of crashing the full study.
