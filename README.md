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

## Development

- Tests are written with the standard `unittest` module:

```bash
python -m unittest discover -s tests
```

- New tools can live under `tools/` and leverage the existing parsing helpers.
