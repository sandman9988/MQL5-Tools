from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import json
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


@dataclasses.dataclass
class Trade:
    ticket: str
    open_time: dt.datetime
    type: str
    volume: float
    symbol: str
    open_price: float
    sl: Optional[float]
    tp: Optional[float]
    close_time: dt.datetime
    close_price: float
    commission: float
    swap: float
    profit: float

    @property
    def cash_flow(self) -> float:
        """Return the full P/L including swap and commission."""
        return self.profit + self.swap + self.commission

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Trade":
        """
        Construct a Trade from a dictionary row. The parser is intentionally
        forgiving about timestamp formats to support a variety of MT4/MT5 exports.
        """

        def parse_dt(value: str) -> dt.datetime:
            attempted_formats: Sequence[str] = (
                "%Y.%m.%d %H:%M:%S",
                "%Y.%m.%d %H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
            )
            for fmt in attempted_formats:
                try:
                    return dt.datetime.strptime(value.strip(), fmt)
                except ValueError:
                    continue
            return dt.datetime.fromisoformat(value.strip())

        def parse_float(value: str) -> Optional[float]:
            if value is None:
                return None
            text = value.strip()
            if text == "":
                return None
            return float(text)

        return cls(
            ticket=row.get("Ticket", "").strip(),
            open_time=parse_dt(row["Open Time"]),
            type=row.get("Type", "").strip(),
            volume=parse_float(row.get("Volume", "0")) or 0.0,
            symbol=row.get("Symbol", "").strip(),
            open_price=parse_float(row.get("Price", "0")) or 0.0,
            sl=parse_float(row.get("SL", "")),
            tp=parse_float(row.get("TP", "")),
            close_time=parse_dt(row["Close Time"]),
            close_price=parse_float(row.get("Close Price", "0")) or 0.0,
            commission=parse_float(row.get("Commission", "0")) or 0.0,
            swap=parse_float(row.get("Swap", "0")) or 0.0,
            profit=parse_float(row.get("Profit", "0")) or 0.0,
        )


def load_trades(path: Path) -> List[Trade]:
    """Load MT4/MT5 CSV exports into a list of Trade objects."""
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        sample = handle.read(2048)
        handle.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        reader = csv.DictReader(handle, dialect=dialect)
        return [Trade.from_row(row) for row in reader]


def gross_profit(trades: Iterable[Trade]) -> float:
    return sum(t.cash_flow for t in trades if t.cash_flow > 0)


def gross_loss(trades: Iterable[Trade]) -> float:
    return sum(abs(t.cash_flow) for t in trades if t.cash_flow < 0)


def equity_curve(trades: Sequence[Trade]) -> List[Tuple[dt.datetime, float]]:
    cumulative = 0.0
    curve: List[Tuple[dt.datetime, float]] = []
    for trade in sorted(trades, key=lambda t: t.close_time):
        cumulative += trade.cash_flow
        curve.append((trade.close_time, cumulative))
    return curve


def max_drawdown(curve: Sequence[Tuple[dt.datetime, float]]) -> float:
    peak = float("-inf")
    max_dd = 0.0
    for _, value in curve:
        peak = max(peak, value)
        max_dd = max(max_dd, peak - value)
    return max_dd


def summarize_trades(trades: Sequence[Trade]) -> dict:
    if not trades:
        return {
            "total_trades": 0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "net_profit": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "average_trade": 0.0,
            "max_drawdown": 0.0,
            "start_date": None,
            "end_date": None,
        }

    gp = gross_profit(trades)
    gl = gross_loss(trades)
    net = gp - gl
    wins = sum(1 for t in trades if t.cash_flow > 0)
    total = len(trades)
    curve = equity_curve(trades)
    start = min(t.open_time for t in trades)
    end = max(t.close_time for t in trades)

    return {
        "total_trades": total,
        "gross_profit": gp,
        "gross_loss": gl,
        "net_profit": net,
        "win_rate": wins / total if total else 0.0,
        "profit_factor": (gp / gl) if gl else float("inf"),
        "average_trade": net / total if total else 0.0,
        "max_drawdown": max_drawdown(curve),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }


def format_summary(summary: dict) -> str:
    lines = [
        f"Total trades : {summary['total_trades']}",
        f"Gross profit : {summary['gross_profit']:.2f}",
        f"Gross loss   : -{summary['gross_loss']:.2f}",
        f"Net profit   : {summary['net_profit']:.2f}",
        f"Win rate     : {summary['win_rate']*100:.2f}%",
        f"Profit factor: {summary['profit_factor']:.2f}",
        f"Average/trade: {summary['average_trade']:.2f}",
        f"Max drawdown : {summary['max_drawdown']:.2f}",
    ]
    if summary["start_date"] and summary["end_date"]:
        lines.append(f"Period       : {summary['start_date']} -> {summary['end_date']}")
    return "\n".join(lines)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize MT4/MT5 trade logs. CSV exports with the standard "
            "Ticket/Open Time/Type/Volume/Symbol/Price/SL/TP/Close Time/Close Price/"
            "Commission/Swap/Profit columns are supported."
        )
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the MT4/MT5 CSV export.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the summary as JSON instead of formatted text.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    trades = load_trades(args.input)
    summary = summarize_trades(trades)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(format_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
