"""Command line for daybook."""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from daybook import __version__
from daybook.invoice import SheetError, load_timesheet, render_invoice


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="daybook",
        description="Turn a timesheet CSV into a client invoice.",
    )
    parser.add_argument("--version", action="version", version=f"daybook {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    invoice = sub.add_parser("invoice", help="Print an invoice for a timesheet.")
    invoice.add_argument("timesheet", type=Path, help="CSV with date, description, hours.")
    invoice.add_argument("--rate", required=True, help="Hourly rate, up to 2 decimal places.")
    invoice.add_argument("--client", required=True, help="Client name.")
    invoice.add_argument("--number", required=True, help="Invoice number.")
    invoice.add_argument("--due", required=True, help="Due date, YYYY-MM-DD.")
    args = parser.parse_args(argv)
    try:
        rate = Decimal(args.rate.strip())
        if not rate.is_finite():
            raise InvalidOperation
    except (InvalidOperation, AttributeError):
        print("daybook: rate is not a number", file=sys.stderr)
        return 1
    try:
        entries = load_timesheet(args.timesheet)
        sys.stdout.write(
            render_invoice(entries, rate, args.client, args.number, args.due)
        )
    except SheetError as exc:
        print(f"daybook: {exc}", file=sys.stderr)
        return 1
    return 0
