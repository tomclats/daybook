"""The invoice command is the product. These tests run it."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACRE = """\
INVOICE 18
Client: Acre Studio
Due: 2026-11-01
Rate: 85.00

date        description            hours    amount
2026-10-01  API review              1.50    127.50
2026-10-02  Fix checkout rounding   3.00    255.00

Hours: 4.50
Total: 382.50
"""


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "daybook", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class InvoiceCommandTest(unittest.TestCase):
    def test_acre_fixture_matches_the_readme_invoice(self) -> None:
        result = run(
            [
                "invoice",
                "fixtures/acre.csv",
                "--rate",
                "85",
                "--client",
                "Acre Studio",
                "--number",
                "18",
                "--due",
                "2026-11-01",
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, ACRE)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(ACRE.strip(), readme)
        amounts = []
        for line in result.stdout.splitlines():
            if line.startswith("2026-"):
                amounts.append(Decimal(line.split()[-1]))
        total_line = next(line for line in result.stdout.splitlines() if line.startswith("Total:"))
        self.assertEqual(sum(amounts, Decimal(0)), Decimal(total_line.split()[-1]))

    def test_same_timesheet_prints_the_same_invoice_twice(self) -> None:
        args = [
            "invoice",
            "fixtures/acre.csv",
            "--rate",
            "85",
            "--client",
            "Acre Studio",
            "--number",
            "18",
            "--due",
            "2026-11-01",
        ]
        first = run(args)
        second = run(args)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)

    def test_line_rounds_half_up_before_the_total(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "week.csv"
            path.write_text("description,hours,date\nReview,1.25,2026-10-03\n", encoding="utf-8")
            result = run(
                [
                    "invoice",
                    str(path),
                    "--rate",
                    "10.10",
                    "--client",
                    "North",
                    "--number",
                    "1",
                    "--due",
                    "2026-10-31",
                ]
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("12.63", result.stdout)
        self.assertIn("Total: 12.63", result.stdout)
        self.assertIn("Hours: 1.25", result.stdout)

    def test_rejects_hours_finer_than_a_hundredth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "week.csv"
            path.write_text("date,description,hours\n2026-10-01,Review,1.005\n", encoding="utf-8")
            result = run(
                ["invoice", str(path), "--rate", "10", "--client", "North", "--number", "1", "--due", "2026-10-31"]
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("more than 2 decimal places", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_rejects_negative_hours(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "week.csv"
            path.write_text("date,description,hours\n2026-10-01,Review,-1\n", encoding="utf-8")
            result = run(
                ["invoice", str(path), "--rate", "10", "--client", "North", "--number", "1", "--due", "2026-10-31"]
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot be negative", result.stderr)


if __name__ == "__main__":
    unittest.main()
