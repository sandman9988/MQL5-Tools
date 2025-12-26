from pathlib import Path
import unittest

from tools import trade_log_analyzer as tla


SAMPLE_PATH = Path(__file__).parent.parent / "examples" / "sample_trades.csv"


class TradeLogAnalyzerTests(unittest.TestCase):
    def test_load_trades(self) -> None:
        trades = tla.load_trades(SAMPLE_PATH)
        self.assertEqual(len(trades), 3)
        self.assertEqual(trades[0].symbol, "EURUSD")
        self.assertAlmostEqual(trades[0].cash_flow, 39.5)

    def test_summary_metrics(self) -> None:
        trades = tla.load_trades(SAMPLE_PATH)
        summary = tla.summarize_trades(trades)

        self.assertEqual(summary["total_trades"], 3)
        self.assertAlmostEqual(summary["gross_profit"], 61.75)
        self.assertAlmostEqual(summary["gross_loss"], 40.8)
        self.assertAlmostEqual(summary["net_profit"], 20.95)
        self.assertAlmostEqual(summary["win_rate"], 2 / 3)
        self.assertAlmostEqual(summary["profit_factor"], 61.75 / 40.8)
        self.assertAlmostEqual(summary["max_drawdown"], 40.8)
        self.assertEqual(summary["start_date"], "2024-01-02T09:00:00")
        self.assertEqual(summary["end_date"], "2024-01-04T18:45:00")


if __name__ == "__main__":
    unittest.main()
