# MQL5 Tools

Utilities for analyzing MetaTrader 4/5 trade exports. The initial toolset focuses on
parsing CSV statements and producing quick risk and performance summaries. The layout
is intentionally simple so it can be expanded with additional scripts or notebooks.

## Inspiration

The VelocityTrader project includes a set of helpful utilities under its `Tools`
directory. Network restrictions in this environment prevented pulling those files
directly, but the structure here is designed to accommodate similar helpers so they
can be slotted in later.

## Current tools

| Tool | Description |
| --- | --- |
| `tools/trade_log_analyzer.py` | CLI/utility functions for summarizing MT4/MT5 CSV trade statements. |
| `tools/mql_compiler.py` | Thin wrapper around the MetaTrader compiler (MetaEditor) for compiling `.mq4/.mq5` sources. |

### Usage

1. Export your trades from MT4/MT5 as CSV with the standard headers:
   `Ticket,Open Time,Type,Volume,Symbol,Price,SL,TP,Close Time,Close Price,Commission,Swap,Profit`.
   The analyzer assumes the **Profit** column excludes commission and swap, which are
   added back in for accurate cash-flow statistics.
2. Run the analyzer:

```bash
python -m tools.trade_log_analyzer path/to/statement.csv
```

Use `--json` to emit machine-readable output:

```bash
python -m tools.trade_log_analyzer path/to/statement.csv --json
```

### Compile MQL sources with a local compiler

The repository now includes a lightweight wrapper around the official MetaEditor
compiler so you can integrate real builds into automation or pre-commit hooks.

```bash
# Point to the MetaTrader compiler (MetaEditor64.exe on Windows). Wine is supported on Linux.
export MQL_COMPILER="/path/to/MetaEditor64.exe"

# Compile a script or Expert Advisor; defaults to writing .ex5/.ex4 next to the source.
python -m tools.mql_compiler path/to/source.mq5

# Override the output path and add extra compiler arguments
python -m tools.mql_compiler path/to/source.mq5 -o build/source.ex5 --extra-arg="/log"
```

When `MQL_COMPILER` is not set, pass `--compiler` explicitly. Add `--wine` if the
compiler executable is a Windows binary running under Wine.

## Development

- Tests are written with the standard `unittest` module:

```bash
python -m unittest discover -s tests
```

- New tools can live under `tools/` and leverage the existing parsing helpers.

### Continuous integration

The CI workflow under `.github/workflows/ci.yml` runs the unit tests on every push/PR
using Python 3.11. It relies only on the standard library so no extra dependencies
are required for a green build.
